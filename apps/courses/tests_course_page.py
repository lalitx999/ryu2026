import os
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from core import testing  # noqa: F401  (py3.14 template-copy shim)
from courses.models import Course, Enrollment, Lesson, Module, Progress
from courses.selectors import course_selector
from payments.models import Payment
from users.models import User

TMP = tempfile.mkdtemp()


@override_settings(PDF_STORAGE_DIR=TMP, MEDIA_ROOT=TMP, SLIPS_STORAGE_DIR=os.path.join(TMP, "slips"), RENEWAL_BONUS_DAYS=3)
class CoursePageBase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        os.makedirs(os.path.join(TMP, "pdfs"), exist_ok=True)       # each class gets its own files (tearDown removes TMP)
        for name in ("free.pdf", "locked.pdf", "shared.pdf"):
            with open(os.path.join(TMP, "pdfs", name), "wb") as fh:
                fh.write(b"%PDF-1.4 test")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.n5 = Course.objects.create(id=1, title="N5", slug="n5", level="N5", price=100, price_180=500, price_365=900)
        cls.n4 = Course.objects.create(id=2, title="N4", slug="n4", level="N4", price=200)
        cls.mod = Module.objects.create(course=cls.n5, title="m", sort_order=1)
        mk = lambda title, **kw: Lesson.objects.create(course=cls.n5, module=cls.mod, title=title, video_url="https://youtu.be/abc", **kw)  # noqa: E731
        cls.free = mk("free", is_free=True, pdf_file="pdfs/free.pdf", sort_order=1)
        cls.locked = mk("locked", pdf_file="pdfs/locked.pdf", sort_order=2)
        cls.shared_free = mk("shared-free", is_free=True, pdf_file="pdfs/shared.pdf", sort_order=3)
        cls.shared_locked = mk("shared-locked", pdf_file="pdfs/shared.pdf", sort_order=4)
        cls.student = User.objects.create_user("s@t.local", "pw123456", name="S")
        cls.other = User.objects.create_user("o@t.local", "pw123456", name="O")
        cls.admin = User.objects.create_user("a@t.local", "pw123456", role="admin", is_staff=True)
        Enrollment.objects.create(user=cls.student, course=cls.n5, is_active=True, status="ACTIVE",
                                  video_expires_at=timezone.localdate() + timedelta(days=10))


class PdfGateTests(CoursePageBase):
    def get(self, user, name):
        self.client.logout()
        if user:
            self.client.force_login(user)
        return self.client.get(f"/storage/protected_pdfs/{name}")

    def test_who_can_open_what(self):
        self.assertEqual(self.get(None, "free.pdf").status_code, 200)             # free lesson: public
        self.assertEqual(self.get(None, "locked.pdf").status_code, 404)           # guest
        self.assertEqual(self.get(self.other, "locked.pdf").status_code, 404)     # no entitlement
        r = self.get(self.student, "locked.pdf")
        self.assertEqual((r.status_code, r["Content-Type"], r["X-Content-Type-Options"]), (200, "application/pdf", "nosniff"))
        self.assertEqual(self.get(self.admin, "locked.pdf").status_code, 200)
        self.assertEqual(self.get(None, "shared.pdf").status_code, 200)           # one file backing a free lesson too

    def test_hostile_and_missing_names(self):
        for name in ("..%2F..%2Fetc%2Fpasswd", "free.txt", "nope.pdf", "%2e%2e%2ffree.pdf"):
            self.assertEqual(self.get(self.admin, name).status_code, 404, name)

    def test_inactive_lesson_file_is_not_served(self):
        Lesson.objects.filter(pk=self.locked.pk).update(is_active=False)
        self.assertEqual(self.get(self.admin, "locked.pdf").status_code, 404)


class OutlineAndProgressTests(CoursePageBase):
    def test_outline_matches_legacy_course_detail_fields(self):
        o = course_selector.course_outline(1, self.student)
        self.assertEqual((o["price"], o["has_access"]), ("100.00", True))
        self.assertTrue({"packages", "thumbnail", "course_description"} <= set(o))
        guest = course_selector.course_outline(1, None)
        locked = [l for m in guest["modules"] for l in m["lessons"] if l["locked"]]
        self.assertTrue(locked and all(l["video_url"] is None and l["pdf_url"] is None for l in locked))   # nothing leaks

    def test_outline_query_count_constant(self):
        with self.assertNumQueries(5):  # access, course, lessons, progress, modules (+ rank)
            course_selector.course_outline(1, self.student)
        for i in range(25):
            Lesson.objects.create(course=self.n5, module=self.mod, title=f"x{i}", video_url="https://youtu.be/z")
        with self.assertNumQueries(5):
            course_selector.course_outline(1, self.student)

    def test_set_completed_toggles_both_ways_and_old_clients_still_work(self):
        self.client.force_login(self.student)
        post = lambda **d: self.client.post("/api/courses/save-progress/", {"lesson_id": self.free.id, **d}, content_type="application/json")  # noqa: E731
        self.assertEqual(post(video_time=30, is_completed=True).json()["data"]["is_completed"], True)     # legacy payload
        self.assertEqual(post(video_time=40, is_completed=False).json()["data"]["is_completed"], True)    # heartbeat never un-completes
        self.assertEqual(post(video_time=40, is_completed=False, set_completed=False).json()["data"]["is_completed"], False)
        self.assertFalse(Progress.objects.get(user=self.student, lesson=self.free).is_completed)
        self.assertEqual(post(set_completed=True).json()["data"]["is_completed"], True)

    def test_page_renders_player_and_dialogs(self):
        html = self.client.get("/courses/1/").content.decode()
        for needle in ("video-player-container", "cb-play", "cb-rate", "cb-full", "btn-prev", "btn-attach", "note-stamp", "authModal", "ryu-boot", "฿100.- / 30 วัน"):
            self.assertIn(needle, html, needle)
        self.client.force_login(self.student)
        html = self.client.get("/courses/1/").content.decode()
        self.assertIn("💳 แจ้งชำระเงินคอร์สนี้", html)
        self.assertNotIn("เข้าสู่ระบบ / สมัครเรียน</button>", html.split("cp-banner")[0])


class CustomRenewalPriceTests(CoursePageBase):
    def upload(self, **data):
        slip = SimpleUploadedFile("s.png", b"\x89PNG\r\n\x1a\n" + b"0" * 20, content_type="image/png")
        body = {"course_id": 1, "duration": 33, "renewal": "1", "slip": slip}
        body.update(data)
        return self.client.post("/api/payments/upload-slip/", body)

    def setUp(self):
        self.client.force_login(self.student)

    def test_without_custom_price_package_price_applies(self):
        r = self.upload(expected_amount="100.00")
        self.assertEqual(r.status_code, 201, r.content)
        p = Payment.objects.get()
        self.assertEqual((p.amount, p.duration_days, p.is_renewal), (Decimal("100.00"), 33, True))

    def test_custom_price_replaces_monthly_price_on_explicit_renewal(self):
        User.objects.filter(pk=self.student.pk).update(custom_renewal_price=Decimal("65.00"))
        self.client.force_login(User.objects.get(pk=self.student.pk))
        self.assertEqual(self.upload(expected_amount="100.00").status_code, 409)       # stale package price is refused
        self.assertEqual(self.upload(expected_amount="65.00").status_code, 201)
        self.assertEqual(Payment.objects.get().amount, Decimal("65.00"))

    def test_custom_price_does_not_touch_other_packages_or_plain_purchase(self):
        User.objects.filter(pk=self.student.pk).update(custom_renewal_price=Decimal("65.00"))
        self.client.force_login(User.objects.get(pk=self.student.pk))
        self.assertEqual(self.upload(duration=180, renewal="", expected_amount="500.00").status_code, 201)
        self.assertEqual(Payment.objects.get().amount, Decimal("500.00"))

    def test_catalog_exposes_renewal_price_only_when_set(self):
        self.assertIsNone(course_selector.catalog(self.student)[0]["renewal_price"])
        User.objects.filter(pk=self.student.pk).update(custom_renewal_price=Decimal("65.00"))
        self.assertEqual(course_selector.catalog(User.objects.get(pk=self.student.pk))[0]["renewal_price"], "65.00")


class ExpiryDisplayTests(CoursePageBase):
    """Students asked where their expiry date is: it must show on the course banner and on the profile course cards."""

    def enroll(self, user, course, days=None, lifetime=False, status="ACTIVE"):
        return Enrollment.objects.create(user=user, course=course, is_active=True, status=status, is_lifetime_video=lifetime,
                                         video_expires_at=None if lifetime else timezone.localdate() + timedelta(days=days))

    def card(self, user, course_id=1):
        return next(c for c in course_selector.catalog(user) if c["id"] == course_id)

    def test_own_enrollment_window(self):
        c = self.card(self.student)
        self.assertEqual((c["access_lifetime"], c["access_until"], c["days_left"]), (False, timezone.localdate() + timedelta(days=10), 10))

    def test_higher_tier_covers_lower_level_and_latest_expiry_wins(self):
        self.enroll(self.other, self.n5, days=5)
        self.enroll(self.other, self.n4, days=40)
        self.assertEqual(self.card(self.other, 1)["days_left"], 40)      # N4 tier also unlocks N5, longer than its own N5 days
        self.assertEqual(self.card(self.other, 2)["days_left"], 40)

    def test_lifetime_and_expired_and_banned(self):
        self.enroll(self.other, self.n5, lifetime=True)
        c = self.card(self.other)
        self.assertEqual((c["access_lifetime"], c["access_until"], c["days_left"]), (True, None, None))
        Enrollment.objects.filter(user=self.other).delete()
        self.enroll(self.other, self.n5, days=-2)                         # expired: nothing to show
        self.assertEqual((self.card(self.other)["access_lifetime"], self.card(self.other)["access_until"]), (False, None))
        Enrollment.objects.filter(user=self.other).delete()
        self.enroll(self.other, self.n5, days=9, status="BANNED")
        self.assertIsNone(self.card(self.other)["access_until"])

    def test_catalog_query_count_unchanged_by_expiry_fields(self):
        with self.assertNumQueries(3):   # courses, progress, enrollments - nothing per course
            course_selector.catalog(self.student)

    def test_course_page_and_profile_show_the_date(self):
        until = timezone.localdate() + timedelta(days=10)
        thai = f"{until.day} {['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.'][until.month - 1]} {until.year + 543}"
        self.client.force_login(self.student)
        for url in ("/courses/1/", "/"):
            html = self.client.get(url).content.decode()
            self.assertIn(f"ใช้ได้ถึง {thai}", html, url)
            self.assertIn("เหลือ 10 วัน", html, url)
        self.client.logout()
        self.assertNotIn("ใช้ได้ถึง", self.client.get("/courses/1/").content.decode())     # guests see no expiry line

    def test_lifetime_banner(self):
        self.enroll(self.other, self.n5, lifetime=True)
        self.client.force_login(self.other)
        self.assertIn("สิทธิ์เรียนตลอดชีพ", self.client.get("/courses/1/").content.decode())

    def test_thai_date_filter(self):
        from datetime import date
        from core.templatetags.ryu import thai_date
        self.assertEqual(thai_date(date(2026, 12, 12)), "12 ธ.ค. 2569")
        self.assertEqual(thai_date("2027-01-05"), "5 ม.ค. 2570")
