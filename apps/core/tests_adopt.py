"""adopt_legacy_db: start from a database shaped like the PHP-era dump (fewer columns, no new tables, untracked by
Django), run the command and check that nothing is lost and everything the models need now exists."""
from io import StringIO

from django.core.management import CommandError, call_command
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase

from community.models import Comment, Post, PostImage, PostLike
from courses.models import Course, GameScore, Note, StudyActivityLog
from payments.models import Payment
from support.models import AraigoguMessage, AraigoguSession
from users.models import EmailVerificationCode, User

NEW_TABLES = [GameScore, Note, StudyActivityLog, Post, PostImage, PostLike, Comment, AraigoguSession, AraigoguMessage, EmailVerificationCode]
# columns the legacy dump does not have (taken from the real dump vs the models)
# (users is left complete here: SQLite's table-rebuild cannot handle AbstractUser's `username = None`; on MySQL the
#  command issues a plain ALTER TABLE.  The users data step is unit-tested separately below.)
LEGACY_LACKS = {
    Course: ["level", "price_180", "price_365", "price_lifetime"],
    Payment: ["is_renewal", "discount_percent"],
}


def cols(table):
    with connection.cursor() as cur:
        return {c.name for c in connection.introspection.get_table_description(cur, table)}


def run(*args):
    out = StringIO()
    call_command("adopt_legacy_db", *args, stdout=out)
    return out.getvalue()


class AdoptLegacyDbTests(TransactionTestCase):
    def setUp(self):
        with connection.schema_editor() as ed:                        # turn the full test schema into a "legacy" one
            for model in NEW_TABLES:
                ed.delete_model(model)
            for model, names in LEGACY_LACKS.items():
                for name in names:
                    ed.remove_field(model, model._meta.get_field(name))
        with connection.cursor() as cur:
            cur.execute("INSERT INTO users (id, name, email, password, role, total_spent, is_affiliate, email_verified, is_active, "
                        "force_password_change, created_at, updated_at, is_staff, is_superuser, first_name, last_name, date_joined, points) VALUES "
                        "(1,'Admin','admin@old.com','$2y$10$abc','admin',0,0,1,1,0,'2025-01-02 03:04:05','2025-01-02 03:04:05',0,0,'','','2030-01-01 00:00:00',0),"
                        "(2,'Stu','stu@old.com','$2y$10$def','student',1500,0,1,1,0,'2025-02-03 04:05:06','2025-02-03 04:05:06',0,0,'','','2030-01-01 00:00:00',0)")
            cur.execute("INSERT INTO courses (id, title, slug, price, is_active, sort_order, created_at, updated_at) VALUES "
                        "(1,'คอร์สเรียน','a',1000,1,1,'2025-01-01 00:00:00','2025-01-01 00:00:00'),"
                        "(2,'คอร์ส JLPT N3 พิเศษ','b',1500,1,2,'2025-01-01 00:00:00','2025-01-01 00:00:00')")
            cur.execute("INSERT INTO payments (id, user_id, course_id, amount, duration_days, is_zoom_included, status, submitted_at) "
                        "VALUES (1,2,1,1000,30,1,'approved','2025-03-01 00:00:00')")
            cur.execute("DELETE FROM django_migrations")                 # legacy DB: Django never tracked it

    def tearDown(self):
        run("--apply", "--force")                                       # leave the schema complete for other tests

    def test_dry_run_changes_nothing_and_explains(self):
        out = run()
        self.assertIn("DRY RUN", out)
        self.assertIn("game_scores", out)
        self.assertIn("level", out)
        self.assertNotIn("level", cols("courses"))
        self.assertNotIn("game_scores", connection.introspection.table_names())

    def test_apply_adds_everything_and_keeps_every_row(self):
        run("--apply")
        names = set(connection.introspection.table_names())
        self.assertTrue({"game_scores", "notes", "community_posts", "araigogu_sessions", "study_activity_logs"} <= names)
        for model, wanted in LEGACY_LACKS.items():
            self.assertTrue(set(wanted) <= cols(model._meta.db_table), model)
        # data preserved
        self.assertEqual(list(User.objects.order_by("id").values_list("email", "password", "total_spent")),
                         [("admin@old.com", "$2y$10$abc", 0), ("stu@old.com", "$2y$10$def", 1500)])
        self.assertEqual(Payment.objects.get().amount, 1000)
        # legacy data steps
        self.assertEqual(dict(Course.objects.values_list("id", "level")), {1: "N5", 2: "N3"})   # id fallback / title match
        self.assertEqual(Course.objects.get(pk=1).price_180, 5000)                              # seeded package prices
        self.assertEqual(Payment.objects.get().is_renewal, False)
        # migrations are recorded, so `migrate` would not recreate tables over the data
        self.assertTrue(MigrationRecorder(connection).migration_qs.filter(app="auth", name="0001_initial").exists())

    def test_users_data_step_makes_admins_staff_and_copies_join_date(self):
        from core.management.commands.adopt_legacy_db import Command
        Command()._data_steps(lambda table, col: table == "users")          # as if is_staff/date_joined had just been added
        a, s = User.objects.get(pk=1), User.objects.get(pk=2)
        self.assertEqual((a.is_staff, s.is_staff), (True, False))
        self.assertEqual(a.date_joined.date().isoformat(), "2025-01-02")

    def test_second_run_is_a_noop_and_tracked_db_is_refused(self):
        run("--apply")
        with self.assertRaises(CommandError):
            run("--apply")                                              # now tracked by Django: refuse without --force
        out = run("--force")
        self.assertIn("สร้างตารางใหม่ 0", out)
        self.assertIn("เพิ่มคอลัมน์: -", out)

    def test_import_legacy_extras_only_into_empty_targets(self):
        with connection.cursor() as cur:
            cur.execute("CREATE TABLE student_notes (id integer primary key, user_id int, course_id int, lesson_id int, note_text text, created_at text, updated_at text)")
            cur.execute("CREATE TABLE game_history (id integer primary key, player_name text, user_id int, difficulty text, score int, correct_count int, total_questions int, played_at text, ip_address text)")
            cur.execute("INSERT INTO lessons (id, course_id, title, sort_order, is_free, is_active, created_at, duration) VALUES (1,1,'L',1,0,1,'2025-01-01 00:00:00',0)")
            cur.execute("INSERT INTO student_notes VALUES (1,2,1,1,'โน้ตเก่า','2025-01-01','2025-01-01'),(2,2,1,1,'โน้ตใหม่กว่า','2025-01-02','2025-01-02')")
            cur.execute("INSERT INTO game_history VALUES (1,'ผู้เล่น',NULL,'easy',900,9,10,'2025-01-01','1.1.1.1')")
        run("--apply", "--import-legacy-extras")
        self.assertEqual(list(Note.objects.values_list("user_id", "lesson_id", "content")), [(2, 1, "โน้ตใหม่กว่า")])   # latest wins
        g = GameScore.objects.get()
        self.assertEqual((g.player_name, g.score, g.game_mode), ("ผู้เล่น", 900, "kana"))
