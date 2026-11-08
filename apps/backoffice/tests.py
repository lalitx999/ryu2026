import json
import shutil
import tempfile
from datetime import timedelta

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from backoffice.selectors import admin_selector
from core import testing  # noqa: F401  (py3.14 template-copy shim)
from courses.models import Course, Enrollment, Lesson, Module, Progress, StudyActivityLog
from payments.models import Payment
from quizzes.models import Quiz, QuizAttempt
from users.models import User

TMP = tempfile.mkdtemp()


def post(client, url, data=None):
    return client.post(url, data or {}, content_type="application/json")


@override_settings(MEDIA_ROOT=TMP, CELERY_TASK_ALWAYS_EAGER=True)
class AdminBase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("admin@t.local", "pw123456", name="Admin", role="admin", is_staff=True)
        cls.student = User.objects.create_user("s@t.local", "pw123456", name="Stu", role="student")
        cls.c5 = Course.objects.create(id=1, title="N5", slug="n5", level="N5", price=1000, price_180=5000, price_365=9000, price_lifetime=10000)

    def setUp(self):
        self.client.force_login(self.admin)


class AccessControlTests(AdminBase):
    def test_student_and_guest_blocked(self):
        for path in ("/admin-panel/", "/admin-panel/sales/", "/admin-panel/courses/1/", "/admin-panel/roles/"):
            self.client.force_login(self.student)
            self.assertEqual(self.client.get(path).status_code, 302, path)
            self.client.logout()
            self.assertEqual(self.client.get(path).status_code, 302, path)
        self.client.force_login(self.student)
        for url in ("/admin-panel/courses/create/", "/admin-panel/lessons/save/", "/admin-panel/users/import/", "/admin-panel/reorder/lessons/"):
            self.assertEqual(post(self.client, url, {"title": "x"}).status_code, 403, url)
        self.assertEqual(self.client.get("/admin-panel/export/payments.csv").status_code, 302)


class CourseAdminTests(AdminBase):
    def test_course_crud_and_delete_guard(self):
        r = post(self.client, "/admin-panel/courses/create/", {"title": "คอร์สใหม่", "level": "N3", "price": "1500"})
        self.assertEqual(r.status_code, 201)
        cid = r.json()["data"]["id"]
        self.assertEqual(post(self.client, f"/admin-panel/courses/{cid}/update/", {"price": "1700", "price_180": "", "is_active": "0"}).status_code, 200)
        c = Course.objects.get(pk=cid)
        self.assertEqual((int(c.price), c.price_180, c.is_active), (1700, None, False))
        self.assertEqual(post(self.client, "/admin-panel/courses/create/", {"title": "x", "level": "N9", "price": "1"}).status_code, 400)
        Enrollment.objects.create(user=self.student, course=self.c5)
        self.assertEqual(post(self.client, "/admin-panel/courses/1/delete/").status_code, 400)   # has students
        self.assertEqual(post(self.client, f"/admin-panel/courses/{cid}/delete/").status_code, 200)

    def test_module_lesson_pdf_reorder(self):
        m = post(self.client, "/admin-panel/modules/save/", {"course_id": 1, "title": "บทที่ 1"}).json()["data"]["id"]
        m2 = post(self.client, "/admin-panel/modules/save/", {"course_id": 1, "title": "บทที่ 2"}).json()["data"]["id"]
        self.assertEqual(Module.objects.get(pk=m2).sort_order, 2)           # auto-appended
        pdf = SimpleUploadedFile("a.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        r = self.client.post("/admin-panel/lessons/save/", {"course_id": 1, "module_id": m, "title": "EP1", "video_url": "https://youtu.be/x", "is_free": "1", "pdf_file": pdf, "pdf_title": "ชีท"})
        self.assertEqual(r.status_code, 201, r.content)
        lesson = Lesson.objects.get()
        self.assertTrue(lesson.pdf_file.name.endswith(".pdf") and lesson.is_free)
        bad = SimpleUploadedFile("a.pdf", b"not a pdf", content_type="application/pdf")
        self.assertEqual(self.client.post(f"/admin-panel/lessons/{lesson.id}/save/", {"pdf_file": bad}).status_code, 400)
        exe = SimpleUploadedFile("a.exe", b"%PDF-", content_type="application/octet-stream")
        self.assertEqual(self.client.post(f"/admin-panel/lessons/{lesson.id}/save/", {"pdf_file": exe}).status_code, 400)
        l2 = post(self.client, "/admin-panel/lessons/save/", {"course_id": 1, "module_id": m, "title": "EP2"}).json()["data"]["id"]
        self.assertEqual(post(self.client, "/admin-panel/reorder/lessons/", {"ids": [l2, lesson.id]}).status_code, 200)
        self.assertEqual(list(Lesson.objects.order_by("sort_order").values_list("id", flat=True)), [l2, lesson.id])
        self.assertEqual(post(self.client, f"/admin-panel/modules/{m}/delete/").status_code, 400)   # not empty
        self.assertEqual(post(self.client, f"/admin-panel/modules/{m2}/delete/").status_code, 200)

    def test_course_detail_query_count_constant(self):
        m = Module.objects.create(course=self.c5, title="m")
        for i in range(3):
            Lesson.objects.create(course=self.c5, module=m, title=f"l{i}")
        with self.assertNumQueries(3):  # course + modules + lessons
            c = admin_selector.course_detail(1)
            [(mm, list(mm.lessons.all())) for mm in c.modules.all()]
        for i in range(30):
            Lesson.objects.create(course=self.c5, module=m, title=f"x{i}")
        with self.assertNumQueries(3):
            c = admin_selector.course_detail(1)
            [(mm, list(mm.lessons.all())) for mm in c.modules.all()]
        self.assertEqual(self.client.get("/admin-panel/courses/1/").status_code, 200)


class UserAdminTests(AdminBase):
    def test_create_user_with_course_and_password(self):
        r = post(self.client, "/admin-panel/users/create/", {"email": "New@T.local", "course_id": 1, "duration_days": 999, "total_spent": "10000"})
        self.assertEqual(r.status_code, 201)
        pw = r.json()["data"]["password_used"]
        u = User.objects.get(email="new@t.local")
        self.assertTrue(u.check_password(pw) and len(pw) >= 8)
        self.assertTrue(Enrollment.objects.get(user=u, course=self.c5).is_lifetime_video)
        self.assertEqual(post(self.client, "/admin-panel/users/create/", {"email": "new@t.local"}).status_code, 400)

    def test_update_entitlements_and_guards(self):
        exp = (timezone.localdate() + timedelta(days=10)).isoformat()
        r = post(self.client, f"/admin-panel/users/{self.student.id}/update/", {"phone": "081", "points": "5", "role": "student",
                 "course_entitlements": [{"course_id": 1, "is_active": True, "is_lifetime": False, "expires_at": exp}]})
        self.assertEqual(r.status_code, 200, r.content)
        e = Enrollment.objects.get(user=self.student)
        self.assertEqual((e.is_active, e.video_expires_at.isoformat()), (True, exp))
        detail = self.client.get(f"/admin-panel/users/{self.student.id}/").json()["data"]
        self.assertEqual(detail["access"][0]["expires_at"], exp)
        self.assertEqual(post(self.client, f"/admin-panel/users/{self.admin.id}/update/", {"role": "student"}).status_code, 400)
        self.assertEqual(post(self.client, f"/admin-panel/users/{self.admin.id}/update/", {"is_active": "0"}).status_code, 400)
        self.assertEqual(post(self.client, f"/admin-panel/users/{self.student.id}/update/", {"password": "123"}).status_code, 400)

    def test_import_students_upserts_and_reports_errors(self):
        rows = [{"email": "a@x.com", "name": "A", "lifetime_levels": "N5"}, {"email": "s@t.local", "name": "Renamed", "total_spent": "5"}, {"email": ""}, {"email": "b@x.com", "total_spent": "10000"}]
        r = post(self.client, "/admin-panel/users/import/", {"students": rows}).json()["data"]
        self.assertEqual((r["imported_count"], r["updated_count"], len(r["errors"])), (2, 1, 1))
        self.assertTrue(Enrollment.objects.get(user__email="a@x.com", course=self.c5).is_lifetime_video)
        self.assertEqual(User.objects.get(email="s@t.local").name, "Renamed")
        self.assertEqual(post(self.client, "/admin-panel/users/import/", {"students": []}).status_code, 400)

    def test_user_detail_query_count(self):
        for i in range(5):
            Course.objects.create(id=10 + i, title=f"c{i}", slug=f"c{i}", level="N4", price=1)
        with self.assertNumQueries(3):  # user + enrollments + courses: constant, not one query per course
            admin_selector.user_detail(self.student.id)


class BroadcastAndReportTests(AdminBase):
    def test_broadcast_targets(self):
        Enrollment.objects.create(user=self.student, course=self.c5, is_active=True, status="ACTIVE")
        User.objects.create_user("other@t.local", "pw123456", role="student")
        r = post(self.client, "/admin-panel/broadcast/send/", {"subject": "Hi", "message": "Body", "target": "course_1"})
        self.assertEqual(r.json()["data"]["total"], 1)
        self.assertEqual(mail.outbox[-1].to, ["s@t.local"])
        self.assertEqual(post(self.client, "/admin-panel/broadcast/send/", {"subject": "Hi", "message": "B", "target": "expired"}).status_code, 400)
        self.assertEqual(post(self.client, "/admin-panel/broadcast/send/", {"subject": "", "message": "B"}).status_code, 400)

    def test_reports_render_with_real_numbers(self):
        p = Payment.objects.create(user=self.student, course=self.c5, amount=1000, status="approved", reviewed_at=timezone.now())
        Payment.objects.create(user=self.student, course=self.c5, amount=500, status="approved", reviewed_at=timezone.now(), is_renewal=True)
        lesson = Lesson.objects.create(course=self.c5, title="L")
        Progress.objects.create(user=self.student, lesson=lesson, is_completed=True)
        StudyActivityLog.objects.create(user=self.student, date=timezone.localdate(), minutes_spent=25, lessons_completed=1)
        quiz = Quiz.objects.create(lesson=lesson, title="q")
        QuizAttempt.objects.create(user=self.student, quiz=quiz, score=8, total_questions=10)
        QuizAttempt.objects.create(user=self.student, quiz=quiz, score=2, total_questions=10)
        r = admin_selector.sales_report()
        self.assertEqual((r["revenue"], r["count"], r["renewal"], r["new"]), (1500.0, 2, 500.0, 1000.0))
        self.assertEqual(r["series"][-1]["amount"], 1500.0)
        a = {m["label"]: m["value"] for m in admin_selector.analytics()["metrics"]}
        self.assertEqual((a["อัตราสอบผ่าน Quiz (≥60%)"], a["นาทีเรียนสะสมทั้งหมด"], a["ผู้เรียนที่ใช้งานวันนี้ (DAU)"]), ("50.0%", "25", "1"))
        for path in ("sales", "analytics", "roles", "settings", "broadcast"):
            self.assertEqual(self.client.get(f"/admin-panel/{path}/").status_code, 200, path)

    def test_csv_export_streams_and_is_excel_safe(self):
        for i in range(3):
            Payment.objects.create(user=self.student, course=self.c5, amount=100 + i, status="approved", reviewed_at=timezone.now())
        resp = self.client.get("/admin-panel/export/payments.csv")
        body = b"".join(resp.streaming_content).decode("utf-8")
        self.assertTrue(body.startswith("﻿id,email"))
        self.assertEqual(len(body.strip().splitlines()), 4)
        self.assertIn("attachment", resp["Content-Disposition"])

    def test_settings_page_never_leaks_secrets(self):
        with override_settings(DEEPSEEK_API_KEY="sk-super-secret-value"):
            html = self.client.get("/admin-panel/settings/").content.decode()
        self.assertNotIn("sk-super-secret-value", html)
        self.assertIn("ตั้งแล้ว", html)


# ───────────────────────── operational screens ─────────────────────────
from io import StringIO  # noqa: E402

from django.core.cache import cache  # noqa: E402
from django.core.management import call_command  # noqa: E402

from community.models import Comment, Post  # noqa: E402
from courses.services import reminder_service  # noqa: E402
from payments.models import SlipBlacklistPattern, SlipVerificationLog  # noqa: E402
from support.models import SupportTicket  # noqa: E402
from system_config.models import LifetimeStudentImport, MigrationRequest, SystemSetting  # noqa: E402


class RenewalReminderTests(AdminBase):
    def setUp(self):
        super().setUp()
        cache.clear()
        today = timezone.localdate()
        mk = lambda email, days, **kw: Enrollment.objects.create(  # noqa: E731
            user=User.objects.create_user(email, "pw123456", name=email.split("@")[0]), course=self.c5, is_active=True,
            video_expires_at=today + timedelta(days=days), **kw)
        self.e3, self.e2, self.e9 = mk("a@x.com", 3), mk("b@x.com", 2), mk("c@x.com", 9)
        self.life = mk("d@x.com", 1, is_lifetime_video=True)
        self.old = mk("e@x.com", -5)

    def test_due_selection_is_exact_and_skips_lifetime(self):
        got = set(reminder_service.due_enrollments().values_list("pk", flat=True))
        self.assertEqual(got, {self.e3.pk, self.e2.pk})
        with_exp = set(reminder_service.due_enrollments(include_expired=True).values_list("pk", flat=True))
        self.assertEqual(with_exp, {self.e3.pk, self.e2.pk, self.old.pk})

    def test_email_content_and_daily_dedupe(self):
        mail.outbox.clear()
        self.assertTrue(reminder_service.send_reminder(self.e3))
        self.assertTrue(reminder_service.send_reminder(self.e3))           # same day: skipped, still "ok"
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEqual(m.to, ["a@x.com"])
        html = m.alternatives[0][0]
        self.assertIn("/courses/1/", html)
        self.assertIn("เหลือเวลาอีก 3 วัน", html)
        self.assertIn("a@x.com", m.body)

    def test_expired_wording_and_html_escaping(self):
        u = self.old.user
        u.name = "<script>x</script>"
        u.save()
        mail.outbox.clear()
        reminder_service.send_reminder(Enrollment.objects.select_related("user", "course").get(pk=self.old.pk))
        html = mail.outbox[0].alternatives[0][0]
        self.assertIn("หมดอายุแล้ว", html)
        self.assertNotIn("<script>x</script>", html)

    def test_management_command_dry_run_and_real(self):
        mail.outbox.clear()
        out = StringIO()
        call_command("send_renewal_reminders", "--dry-run", stdout=out)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("2 sent/queued", out.getvalue())
        call_command("send_renewal_reminders", stdout=StringIO())
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["a@x.com", "b@x.com"])

    def test_admin_endpoint_selected_and_criteria(self):
        mail.outbox.clear()
        r = post(self.client, "/admin-panel/renewals/send/", {"enrollment_ids": [self.e9.pk, self.life.pk]})
        self.assertEqual(r.json()["data"]["sent"], 1)                      # lifetime is never reminded
        self.assertEqual(post(self.client, "/admin-panel/renewals/send/", {"enrollment_ids": [self.life.pk]}).status_code, 400)
        r = post(self.client, "/admin-panel/renewals/send/", {"days": [3, 2]})
        self.assertEqual(r.json()["data"]["sent"], 2)
        self.assertEqual(self.client.get("/admin-panel/renewals/").status_code, 200)

    def test_list_query_count_is_constant(self):
        with self.assertNumQueries(1):
            list(reminder_service.expiring_list())
        from backoffice.selectors import ops_selector
        with self.assertNumQueries(1):
            ops_selector.renewals()


class OpsScreenTests(AdminBase):
    def test_moderation_actions(self):
        post_ = Post.objects.create(user=self.student, title="t", content="rude", moderation_status="PENDING")
        c = Comment.objects.create(user=self.student, post=post_, content="c", moderation_status="PENDING")
        self.assertEqual(post(self.client, f"/admin-panel/community/posts/{post_.id}/moderate/", {"action": "reject"}).status_code, 200)
        self.assertEqual(Post.objects.get().moderation_status, "REJECTED")
        self.assertEqual(post(self.client, f"/admin-panel/community/comments/{c.id}/moderate/", {"action": "approve"}).status_code, 200)
        self.assertEqual(Comment.objects.get().moderation_status, "APPROVED")
        self.assertEqual(post(self.client, f"/admin-panel/community/posts/{post_.id}/moderate/", {"action": "hack"}).status_code, 400)
        self.assertEqual(post(self.client, "/admin-panel/community/users/1/moderate/", {"action": "delete"}).status_code, 400)
        for url in ("/admin-panel/community/", "/admin-panel/community/?kind=comments&status=APPROVED"):
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(post(self.client, f"/admin-panel/community/posts/{post_.id}/moderate/", {"action": "delete"}).status_code, 200)
        self.assertFalse(Post.objects.exists())

    def test_tickets_and_migrations(self):
        t = SupportTicket.objects.create(user=self.student, category="วิดีโอ", message="เล่นไม่ได้")
        post(self.client, f"/admin-panel/tickets/{t.id}/action/", {"action": "resolve"})
        self.assertEqual(SupportTicket.objects.get().status, "resolved")
        self.assertEqual(post(self.client, f"/admin-panel/tickets/{t.id}/action/", {"action": "x"}).status_code, 400)
        m = MigrationRequest.objects.create(email="old@x.com", tracking_code="T1")
        post(self.client, f"/admin-panel/migrations/{m.id}/action/", {"action": "approve", "note": "ok"})
        m.refresh_from_db()
        self.assertEqual((m.status, m.admin_note, m.processed_by), ("approved", "ok", self.admin.id))
        self.assertIsNotNone(m.processed_at)
        post(self.client, f"/admin-panel/migrations/{m.id}/action/", {"action": "reopen"})
        m.refresh_from_db()
        self.assertIsNone(m.processed_at)
        LifetimeStudentImport.objects.create(email="l@x.com", level="N5", invite_code="ABC")
        for url in ("/admin-panel/tickets/", "/admin-panel/migrations/", "/admin-panel/migrations/?q=ABC&status=pending"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_slip_rules_and_logs(self):
        r = post(self.client, "/admin-panel/slips/rules/add/", {"type": "keyword", "pattern": "fake-bank"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(post(self.client, "/admin-panel/slips/rules/add/", {"type": "keyword", "pattern": "FAKE-BANK"}).status_code, 400)
        self.assertEqual(post(self.client, "/admin-panel/slips/rules/add/", {"type": "bogus", "pattern": "x"}).status_code, 400)
        pay = Payment.objects.create(user=self.student, course=self.c5, amount=100)
        SlipVerificationLog.objects.create(payment=pay, user=self.student, status="suspicious", error_message="mismatch")
        self.assertIn("fake-bank", self.client.get("/admin-panel/slips/").content.decode())
        self.assertEqual(post(self.client, f"/admin-panel/slips/rules/{r.json()['data']['id']}/delete/").status_code, 200)
        self.assertFalse(SlipBlacklistPattern.objects.exists())

    def test_payment_detail(self):
        pay = Payment.objects.create(user=self.student, course=self.c5, amount=1000, slip_path="x.jpg")
        SlipVerificationLog.objects.create(payment=pay, user=self.student, status="approved", verified_amount=1000, verified_bank="ttb")
        with self.assertNumQueries(4):  # session, user, payment(+joins), latest log  (constant)
            d = self.client.get(f"/admin-panel/payments/{pay.id}/").json()["data"]
        self.assertEqual((d["amount"], d["has_slip"], d["easyslip"]["bank"]), ("1000.00", True, "ttb"))
        self.assertEqual(self.client.get("/admin-panel/payments/9999/").status_code, 404)

    def test_settings_superuser_only_and_values_hidden(self):
        self.assertEqual(post(self.client, "/admin-panel/settings/save/", {"key": "k", "value": "v"}).status_code, 403)   # plain admin
        root = User.objects.create_user("root@t.local", "pw123456", role="admin", is_staff=True, is_superuser=True)
        self.client.force_login(root)
        self.assertEqual(post(self.client, "/admin-panel/settings/save/", {"key": "smtp.pass", "value": "TOP-SECRET-123"}).status_code, 200)
        self.assertEqual(post(self.client, "/admin-panel/settings/save/", {"key": "bad key!", "value": "v"}).status_code, 400)
        self.assertEqual(SystemSetting.objects.get(pk="smtp.pass").key_value, "TOP-SECRET-123")
        html = self.client.get("/admin-panel/settings/").content.decode()
        self.assertIn("smtp.pass", html)
        self.assertNotIn("TOP-SECRET-123", html)
        self.assertEqual(post(self.client, "/admin-panel/settings/delete/", {"key": "smtp.pass"}).status_code, 200)
        self.assertFalse(SystemSetting.objects.exists())

    def test_students_blocked_from_ops(self):
        self.client.force_login(self.student)
        for p in ("community/", "tickets/", "migrations/", "slips/", "renewals/"):
            self.assertEqual(self.client.get(f"/admin-panel/{p}").status_code, 302, p)
        for u in ("/admin-panel/renewals/send/", "/admin-panel/slips/rules/add/", "/admin-panel/community/posts/1/moderate/", "/admin-panel/settings/save/"):
            self.assertEqual(post(self.client, u, {}).status_code, 403, u)
        self.assertEqual(self.client.get("/admin-panel/payments/1/").status_code, 403)


class AdminPolishTests(AdminBase):
    def test_per_page_whitelist(self):
        for i in range(30):
            User.objects.create_user(f"u{i}@t.local", "pw123456", name=f"U{i}")
        from backoffice.selectors import admin_selector
        self.assertEqual(admin_selector.page_size("50"), 50)
        self.assertEqual(admin_selector.page_size("100000"), 20)
        self.assertEqual(admin_selector.page_size("abc"), 20)
        html = self.client.get("/admin-panel/users/?per_page=10").content.decode()
        self.assertEqual(html.count("data-edit-user="), 10)
        self.assertIn("10 รายการต่อหน้า", html)
        self.assertEqual(self.client.get("/admin-panel/payments/?per_page=50").status_code, 200)

    def test_sort_lessons_by_number_in_title(self):
        m = Module.objects.create(course=self.c5, title="m")
        titles = ["บทที่ 10", "บทที่ 2", "ไม่มีเลข", "บทที่ 1"]
        ids = [Lesson.objects.create(course=self.c5, module=m, title=t, sort_order=i + 1).id for i, t in enumerate(titles)]
        r = post(self.client, f"/admin-panel/modules/{m.id}/sort/")
        self.assertEqual(r.status_code, 200)
        order = list(Lesson.objects.filter(module=m).order_by("sort_order").values_list("title", flat=True))
        self.assertEqual(order, ["บทที่ 1", "บทที่ 2", "บทที่ 10", "ไม่มีเลข"])
        self.assertEqual(post(self.client, "/admin-panel/modules/99999/sort/").status_code, 404)

    def test_course_card_saves_description_level_and_order(self):
        r = post(self.client, "/admin-panel/courses/1/update/", {"title": "N5", "price": "100", "level": "N4", "description": "รายละเอียดใหม่", "sort_order": "7"})
        self.assertEqual(r.status_code, 200, r.content)
        c = Course.objects.get(pk=1)
        self.assertEqual((c.level, c.description, c.sort_order), ("N4", "รายละเอียดใหม่", 7))

    def test_login_copy(self):
        self.client.logout()
        self.assertIn("เข้าสู่ระบบ Admin Portal", self.client.get("/admin-panel/login/").content.decode())
        self.client.force_login(self.student)
        r = post(self.client, "/admin-panel/api/login/", {"email": "s@t.local", "password": "pw123456"})
        self.assertIn("Staff/Admin Only", r.json()["error"])
