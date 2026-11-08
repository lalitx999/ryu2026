"""Bring an EXISTING legacy RyuClass database (PHP/older Django era) up to this project's schema without
re-creating it and without losing a row.

    python manage.py adopt_legacy_db            # dry run: prints exactly what would change
    python manage.py adopt_legacy_db --apply    # does it
    python manage.py migrate                    # afterwards: no-op, but creates permissions / content types

What it does (only ever *adds*; nothing is dropped, renamed or rewritten):
  1. creates tables the models need but the database lacks (auth/session tables, community, Araigogu, ...);
  2. adds the columns the models need to tables that already exist (users, courses, lessons, payments, ...);
  3. repeats the legacy data steps on the new columns (course level N1..N5, package prices, is_staff for admins);
  4. records every migration as applied, so `migrate` will not try to CREATE TABLE over your data.
New tables get no FOREIGN KEY constraints: the legacy ids are INT UNSIGNED and MySQL refuses a signed FK to them
(the models already use db_constraint=False for the same reason).
"""
import importlib

from django.apps import apps as django_apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import F


class Command(BaseCommand):
    help = "Adopt an existing legacy database into this project (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="execute the plan (default: only print it)")
        parser.add_argument("--import-legacy-extras", action="store_true",
                            help="also copy old student_notes -> notes and game_history -> game_scores (only into empty tables)")
        parser.add_argument("--force", action="store_true", help="run even if Django already tracks migrations in this DB")

    # ───────────────────────── planning ─────────────────────────
    def _plan(self):
        existing = set(connection.introspection.table_names())
        creates, adds = [], []
        with connection.cursor() as cur:
            for model in django_apps.get_models(include_auto_created=True):
                meta = model._meta
                if not meta.managed or meta.proxy or meta.swapped:
                    continue
                if meta.db_table not in existing:
                    creates.append(model)
                    continue
                have = {c.name for c in connection.introspection.get_table_description(cur, meta.db_table)}
                adds += [(model, f) for f in meta.local_fields if f.column not in have]
        return existing, creates, adds

    def handle(self, *args, **opts):
        recorder = MigrationRecorder(connection)
        tracked = recorder.has_table() and recorder.applied_migrations()
        if tracked and not opts["force"]:
            raise CommandError("ฐานข้อมูลนี้มีตาราง django_migrations ที่บันทึกไว้แล้ว (Django ดูแลอยู่) - ไม่ต้องใช้คำสั่งนี้ "
                               "รัน `python manage.py migrate` ได้เลย (หรือใส่ --force ถ้าแน่ใจ)")
        existing, creates, adds = self._plan()
        by_table = {}
        for model, field in adds:
            by_table.setdefault(model._meta.db_table, []).append(field.column)
        col_added = lambda table, col: col in by_table.get(table, [])  # noqa: E731

        self.stdout.write(self.style.MIGRATE_HEADING("แผนการปรับฐานข้อมูล" + ("" if opts["apply"] else " (DRY RUN - ยังไม่แก้อะไร)")))
        self.stdout.write(f"  สร้างตารางใหม่ {len(creates)}: " + (", ".join(m._meta.db_table for m in creates) or "-"))
        for table, cols in by_table.items():
            self.stdout.write(f"  เพิ่มคอลัมน์ใน {table}: {', '.join(cols)}")
        if not by_table:
            self.stdout.write("  เพิ่มคอลัมน์: -")
        steps = []
        if col_added("courses", "level"):
            steps.append("กำหนด level (N1-N5) ให้คอร์สเดิมจากชื่อ/slug/รหัส (เหมือน migration courses.0008)")
        if col_added("courses", "price_180"):
            steps.append("ใส่ราคา 6 เดือน/1 ปี/ตลอดชีพ เริ่มต้นให้คอร์สรหัส 1-5 (เหมือน migration courses.0005) - ตรวจ/แก้ในหน้าแอดมินหลังจากนั้น")
        if col_added("users", "is_staff"):
            steps.append("ตั้ง is_staff=True ให้ผู้ใช้ role=admin และ date_joined=created_at")
        for s in steps:
            self.stdout.write("  ข้อมูล: " + s)
        graph_nodes = MigrationLoader(connection, ignore_no_migrations=True).graph.nodes
        self.stdout.write(f"  บันทึก migration ว่าทำแล้ว: {len(graph_nodes)} รายการ (กัน migrate สร้างตารางทับข้อมูลเดิม)")
        if opts["import_legacy_extras"]:
            self.stdout.write("  คัดลอก: student_notes -> notes, game_history -> game_scores (เฉพาะปลายทางที่ว่างเท่านั้น)")
        if not opts["apply"]:
            self.stdout.write(self.style.WARNING("\nนี่คือ dry run — สำรองฐานข้อมูลแล้วรันซ้ำพร้อม --apply เพื่อดำเนินการจริง"))
            return

        # ───────────────────────── apply ─────────────────────────
        with connection.schema_editor() as editor:
            for model in creates:
                editor.create_model(model)
            for model, field in adds:
                with connection.cursor() as cur:   # a backend may add several columns at once (SQLite rebuilds the table)
                    have = {c.name for c in connection.introspection.get_table_description(cur, model._meta.db_table)}
                if field.column not in have:
                    editor.add_field(model, field)
            # keep the legacy style: no DB-level FKs on tables we create (signed/unsigned id mismatch on MySQL)
            editor.deferred_sql = [s for s in editor.deferred_sql if "FOREIGN KEY" not in str(s).upper()]
        self.stdout.write(self.style.SUCCESS("  โครงสร้างตารางเรียบร้อย"))

        with transaction.atomic():
            self._data_steps(col_added)
            if opts["import_legacy_extras"]:
                self._legacy_extras(existing)
        self.stdout.write(self.style.SUCCESS("  ข้อมูลเริ่มต้นเรียบร้อย"))

        recorder.ensure_schema()
        for app_label, name in graph_nodes:
            if not recorder.migration_qs.filter(app=app_label, name=name).exists():
                recorder.record_applied(app_label, name)
        pending = MigrationExecutor(connection).migration_plan(MigrationExecutor(connection).loader.graph.leaf_nodes())
        self.stdout.write(self.style.SUCCESS(f"  บันทึก migration แล้ว  งานค้าง: {len(pending)}"))
        self.stdout.write("เสร็จแล้ว → รัน `python manage.py migrate` อีกครั้งเพื่อสร้างสิทธิ์/content types แล้วตรวจ `python manage.py check`")

    # ───────────────────────── data ─────────────────────────
    def _data_steps(self, col_added):
        from users.models import User

        if col_added("courses", "level"):
            mod = importlib.import_module("courses.migrations.0008_course_level")
            mod.populate_course_levels(django_apps, None)
        if col_added("courses", "price_180"):
            mod = importlib.import_module("courses.migrations.0005_course_package_prices")

            class _Editor:                       # seed_prices only needs the connection alias
                connection = connection
            mod.seed_prices(django_apps, _Editor)
        if col_added("users", "is_staff"):
            User.objects.filter(role="admin").update(is_staff=True)
        if col_added("users", "date_joined"):
            User.objects.update(date_joined=F("created_at"))

    def _legacy_extras(self, existing):
        from courses.models import GameScore, Note

        with connection.cursor() as cur:
            if "student_notes" in existing and not Note.objects.exists():
                cur.execute("SELECT user_id, lesson_id, note_text, created_at, updated_at FROM student_notes ORDER BY id")
                for user_id, lesson_id, text, created, updated in cur.fetchall():
                    if not lesson_id or not user_id:
                        continue
                    Note.objects.update_or_create(user_id=user_id, lesson_id=lesson_id, defaults={"content": text or ""})
                n = Note.objects.count()
                self.stdout.write(f"    notes ← student_notes: {n} แถว")
            if "game_history" in existing and not GameScore.objects.exists():
                cur.execute("SELECT user_id, player_name, score, played_at FROM game_history ORDER BY id")
                rows = [GameScore(user_id=u, player_name=(p or "")[:50], game_mode="kana", jlpt_level="N5", score=int(s or 0))
                        for u, p, s, _ in cur.fetchall()]
                GameScore.objects.bulk_create(rows, batch_size=500)
                self.stdout.write(f"    game_scores ← game_history: {len(rows)} แถว")
