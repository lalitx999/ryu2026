"""The all-access plan (960 / month, 9,600 / year, N5-N1) that replaces the per-level prices on SINGLE_PLAN_START.

PLAN_ON / PLAN_OFF move the switch date instead of the clock, so these tests mean the same thing on any day."""
import datetime
import os
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from core import testing  # noqa: F401  (py3.14 template-copy shim)
from courses.models import Course, Enrollment
from courses.pricing import single_plan_active
from courses.selectors import course_selector
from courses.services.access_service import AccessService
from microsites import registry
from payments.models import Payment
from payments.services import payment_service
from users.models import User

TMP = tempfile.mkdtemp()
PLAN_ON = override_settings(SINGLE_PLAN_START=datetime.date(2000, 1, 1))
PLAN_OFF = override_settings(SINGLE_PLAN_START=datetime.date(2099, 1, 1))
LEARN = registry.BY_KEY["learn"].host


def slip():
    return SimpleUploadedFile("s.png", b"\x89PNG\r\n\x1a\n" + b"0" * 20, content_type="image/png")


@override_settings(SLIPS_STORAGE_DIR=os.path.join(TMP, "slips"), MEDIA_ROOT=TMP, RENEWAL_BONUS_DAYS=3,
                   SINGLE_PLAN_MONTHLY=960, SINGLE_PLAN_YEARLY=9600,
                   EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PlanBase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        prices = {"N5": 1000, "N4": 1250, "N3": 1500, "N2": 1750, "N1": 2000}
        cls.courses = {lvl: Course.objects.create(id=i, title=f"คอร์ส {lvl}", slug=lvl.lower(), level=lvl, sort_order=i,
                                                  price=p, price_180=p * 5, price_365=p * 9, price_lifetime=p * 10)
                       for i, (lvl, p) in enumerate(prices.items(), start=1)}
        cls.student = User.objects.create_user("s@t.local", "pw123456", name="S")

    def setUp(self):
        self.client.force_login(self.student)

    def upload(self, **data):
        body = {"course_id": self.courses["N5"].id, "duration": 30, "slip": slip()}
        body.update(data)
        return self.client.post("/api/payments/upload-slip/", body)


class SwitchDateTests(PlanBase):
    def test_switch_is_inclusive_on_the_start_date(self):
        with override_settings(SINGLE_PLAN_START=datetime.date(2026, 12, 1)):
            self.assertFalse(single_plan_active(datetime.date(2026, 11, 30)))
            self.assertTrue(single_plan_active(datetime.date(2026, 12, 1)))

    @PLAN_OFF
    def test_before_the_switch_nothing_changes(self):
        r = self.upload(course_id=self.courses["N3"].id, duration=180, expected_amount="7500")
        self.assertEqual(r.status_code, 201, r.content)
        p = Payment.objects.get()
        self.assertEqual((p.course.level, p.amount, p.level_access), ("N3", Decimal("7500"), "N3"))
        self.assertEqual(self.upload(duration=33, renewal="1", expected_amount="1000").status_code, 201)  # bonus days
        self.assertIsNone(course_selector.plan())
        self.assertEqual(len(course_selector.price_table()), 5)


@PLAN_ON
class PlanPurchaseTests(PlanBase):
    def test_any_course_buys_the_plan_at_the_plan_price(self):
        r = self.upload(course_id=self.courses["N5"].id, duration=30, expected_amount="960")
        self.assertEqual(r.status_code, 201, r.content)
        p = Payment.objects.get()
        self.assertEqual((p.course.level, p.amount, p.duration_days, p.level_access, p.is_zoom_included),
                         ("N1", Decimal("960"), 30, "N5-N1", True))

    def test_yearly_costs_9600(self):
        self.assertEqual(self.upload(duration=365, expected_amount="9600").status_code, 201)
        self.assertEqual(Payment.objects.get().amount, Decimal("9600"))

    def test_six_month_lifetime_and_bonus_durations_are_closed(self):
        for days, amount in ((180, "4800"), (9999, "20000"), (33, "960")):
            r = self.upload(duration=days, expected_amount=amount)
            self.assertEqual(r.status_code, 400, (days, r.content))
        self.assertFalse(Payment.objects.exists())

    def test_old_price_on_a_stale_page_is_refused(self):
        self.assertEqual(self.upload(expected_amount="1000").status_code, 409)   # page opened before midnight
        self.assertFalse(Payment.objects.exists())

    def test_renewal_is_30_days_and_ignores_the_personal_price(self):
        User.objects.filter(pk=self.student.pk).update(custom_renewal_price=Decimal("650"))
        self.client.force_login(User.objects.get(pk=self.student.pk))
        self.assertEqual(self.upload(renewal="1", expected_amount="650").status_code, 409)
        self.assertEqual(self.upload(renewal="1", expected_amount="960").status_code, 201)
        p = Payment.objects.get()
        self.assertEqual((p.amount, p.duration_days, p.is_renewal), (Decimal("960"), 30, True))
        self.assertIsNone(course_selector.catalog(User.objects.get(pk=self.student.pk))[0]["renewal_price"])

    def test_signup_with_any_level_buys_the_plan(self):
        self.client.logout()
        r = self.client.post("/api/auth/register/", {
            "name": "New", "email": "new@t.local", "password": "pw123456", "phone": "0800000000",
            "level": "N3", "duration": "365", "expected_amount": "9600", "slip": slip()})
        self.assertEqual(r.status_code, 201, r.content)
        p = Payment.objects.get(user__email="new@t.local")
        self.assertEqual((p.course.level, p.amount, p.level_access, p.is_zoom_included), ("N1", Decimal("9600"), "N5-N1", True))

    def test_signup_without_a_level_works(self):
        self.client.logout()
        r = self.client.post("/api/auth/register/", {
            "name": "New", "email": "new2@t.local", "password": "pw123456", "phone": "0800000000",
            "duration": "30", "expected_amount": "960", "slip": slip()})
        self.assertEqual(r.status_code, 201, r.content)


@PLAN_ON
class PlanApprovalTests(PlanBase):
    def test_approved_plan_unlocks_every_level(self):
        self.upload(expected_amount="960")
        payment_service.approve_payment(Payment.objects.get().id)
        for lvl in ("N5", "N4", "N3", "N2", "N1"):
            self.assertTrue(AccessService.has_video_access(self.student.id, lvl), lvl)
        e = Enrollment.objects.get(user=self.student)
        self.assertEqual(e.video_expires_at, timezone.localdate() + timedelta(days=30))

    def test_early_renewal_keeps_the_days_already_paid(self):
        today = timezone.localdate()
        Enrollment.objects.create(user=self.student, course=self.courses["N5"], is_active=True, status="ACTIVE",
                                  video_expires_at=today + timedelta(days=3))
        self.upload(renewal="1", expected_amount="960")
        payment_service.approve_payment(Payment.objects.get().id)
        n1 = Enrollment.objects.get(user=self.student, course=self.courses["N1"])
        self.assertEqual(n1.video_expires_at, today + timedelta(days=33))

    def test_old_price_slip_approved_after_the_switch_keeps_what_was_bought(self):
        old = Payment.objects.create(user=self.student, course=self.courses["N4"], amount=Decimal("1250"),
                                     duration_days=33, level_access="N4", status="pending", slip_path="x.png")
        payment_service.approve_payment(old.id)
        e = Enrollment.objects.get(user=self.student)
        self.assertEqual((e.course.level, e.video_expires_at), ("N4", timezone.localdate() + timedelta(days=33)))
        self.assertFalse(AccessService.has_video_access(self.student.id, "N3"))

    def test_spend_based_lifetime_unlocks_are_untouched(self):
        User.objects.filter(pk=self.student.pk).update(total_spent=Decimal("9600"))
        self.upload(expected_amount="960")
        payment_service.approve_payment(Payment.objects.get().id)
        self.assertTrue(Enrollment.objects.get(user=self.student, course=self.courses["N5"]).is_lifetime_video)


@PLAN_ON
@override_settings(ALLOWED_HOSTS=["testserver", *registry.all_hosts()], SITE_URL="https://www.ryusosense.online")
class PlanPageTests(PlanBase):
    def test_salepage_shows_one_plan_card(self):
        html = self.client.get("/salepage/").content.decode()
        for text in ("960 ฿", "9,600 ฿", "ประหยัด 1,920 ฿", "เรียนได้ทุกระดับ N5–N1"):
            self.assertIn(text, html)
        self.assertNotIn("6 เดือน", html)
        self.assertNotIn("10,000 ฿", html)       # old N5 lifetime package price

    def test_microsite_sales_page_shows_the_plan(self):
        html = self.client.get("/", HTTP_HOST=LEARN).content.decode()
        self.assertIn("฿9,600", html)
        self.assertIn("เริ่มต้นเดือนละ ฿960", html)
        self.assertNotIn("6 เดือน", html)

    def test_course_page_and_dialogs(self):
        html = self.client.get(f"/courses/{self.courses['N3'].id}/").content.decode()
        self.assertIn('href="/salepage/#pricing-section"', html)   # price lives behind the details link
        self.assertIn("ทุกระดับ N5–N1", html)
        self.assertIn('"renewalDays": 30', html)
        self.assertNotIn("33 วัน", html)

    def test_structured_data_offers_the_plan(self):
        html = self.client.get("/").content.decode()
        self.assertIn('"lowPrice": "960"', html)
        self.assertIn('"highPrice": "9600"', html)
