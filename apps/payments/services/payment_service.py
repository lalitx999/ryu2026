"""Payment use-cases: price validation, slip intake, approve / reject.  No HTTP, no external calls."""
import os
import time
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.http import ServiceError
from courses.models import Course, Enrollment
from courses.pricing import package_amount
from courses.services.access_service import AccessService
from payments.models import Payment

ALLOWED_SLIP_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif"}


def expected_amount(course, days, client_amount, override=None):
    """Server-side price is authoritative; the client sends what it *saw* so stale pages are rejected.
    `override` is a per-student renewal price set by an admin (replaces the 30-day package price)."""
    try:
        amount = override if override else package_amount(course, days)
    except (ValueError, TypeError) as exc:
        raise ServiceError(str(exc))
    try:
        seen = Decimal(str(client_amount))
        if not seen.is_finite() or seen != amount:
            raise ServiceError("ราคามีการเปลี่ยนแปลง กรุณาปิดแล้วเปิดหน้าชำระเงินใหม่เพื่อตรวจสอบยอดก่อนโอน", status=409)
    except InvalidOperation:
        raise ServiceError("กรุณาโหลดหน้าชำระเงินใหม่เพื่อยืนยันราคา")
    return amount


def _store_slip(slip_file, user_id):
    ext = os.path.splitext(slip_file.name)[1].lower()
    if ext not in ALLOWED_SLIP_EXT:
        raise ServiceError("รองรับเฉพาะไฟล์ภาพสลิป (JPG, PNG, WEBP)")
    if slip_file.size > settings.MAX_SLIP_BYTES:
        raise ServiceError("ไฟล์สลิปใหญ่เกิน 8MB")
    directory = settings.SLIPS_STORAGE_DIR
    os.makedirs(directory, exist_ok=True)
    filename = f"slip_{user_id}_{int(time.time())}{ext}"
    path = os.path.join(directory, filename)
    with open(path, "wb") as out:
        for chunk in slip_file.chunks():
            out.write(chunk)
    return filename


@transaction.atomic
def submit_slip_payment(*, user, course, amount, duration_days, slip_file, is_zoom_included, is_renewal):
    filename = _store_slip(slip_file, user.id)
    payment = Payment.objects.create(
        user=user, course=course, amount=amount, duration_days=duration_days, level_access=course.level,
        is_zoom_included=is_zoom_included, slip_path=filename, status="pending", is_renewal=is_renewal,
        discount_percent=0,
    )
    from payments import tasks  # local import: avoids a cycle at app loading

    # EasySlip + Telegram are slow/external -> Celery, and only after the row is committed.
    transaction.on_commit(lambda: tasks.process_new_slip.delay(payment.id))
    return payment


def upload_slip_existing_user(user, data, slip_file):
    """Logged-in student buys / renews a course."""
    course = Course.objects.filter(id=data.get("course_id") or 0, is_active=True).first()
    if course is None or not slip_file:
        raise ServiceError("กรุณากรอกข้อมูลและแนบสลิปการโอนเงินให้ครบถ้วนครับ")
    try:
        days = int(data.get("duration"))
    except (TypeError, ValueError):
        raise ServiceError("ระยะเวลาเรียนไม่ถูกต้อง")
    bonus = settings.RENEWAL_BONUS_DAYS
    renewal_requested = str(data.get("renewal", "")).lower() in ("1", "true", "yes")
    has_active = Enrollment.objects.filter(user=user, course=course, is_active=True, is_lifetime_video=False).exists()
    is_renewal = renewal_requested or has_active
    price_days = days
    if is_renewal and days == 30:
        days = 30 + bonus
    elif days == 30 + bonus:
        price_days = 30
    # admin-set "ราคาต่ออายุเฉพาะบุคคล": applies to an explicit renewal of the monthly package only
    custom = user.custom_renewal_price if renewal_requested and price_days == 30 else None
    amount = expected_amount(course, price_days, data.get("expected_amount"), override=custom)
    payment = submit_slip_payment(user=user, course=course, amount=amount, duration_days=days,
                                  slip_file=slip_file, is_zoom_included=days >= 30, is_renewal=is_renewal)
    return payment


@transaction.atomic
def approve_payment(payment_id, reviewed_by=None, trans_ref=None):
    """Single approval path (admin click or EasySlip).  Row-locked so it can never double-count."""
    payment = Payment.objects.select_for_update().select_related("user", "course").get(pk=payment_id)
    if payment.status == "approved":
        return payment
    user = payment.user
    user.total_spent = Decimal(str(user.total_spent or "0")) + Decimal(str(payment.amount or "0"))
    user.save(update_fields=["total_spent"])
    AccessService.recalculate_lifetime_unlocks(user.id)

    enrollment, _ = Enrollment.objects.get_or_create(user=user, course=payment.course)
    today = timezone.localdate()
    enrollment.is_active, enrollment.status = True, "ACTIVE"
    enrollment.payment_id, enrollment.activated_at = payment.id, timezone.now()
    if payment.duration_days >= 999:
        enrollment.is_lifetime_video = True
    else:
        enrollment.video_expires_at = max(enrollment.video_expires_at or today, today) + timedelta(days=payment.duration_days)
        if payment.is_zoom_included:
            enrollment.zoom_expires_at = max(enrollment.zoom_expires_at or today, today) + timedelta(days=payment.duration_days)
    enrollment.save()

    payment.status, payment.rejection_reason = "approved", ""
    if trans_ref:
        payment.trans_ref = trans_ref
    payment.reviewed_at = timezone.now()
    if reviewed_by:
        payment.reviewed_by = reviewed_by
    payment.save()

    from users.tasks import send_welcome_email
    transaction.on_commit(lambda: send_welcome_email.delay(user.email))
    return payment


@transaction.atomic
def reject_payment(payment_id, reviewed_by, reason=""):
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    if payment.status == "approved":
        raise ServiceError("รายการนี้อนุมัติไปแล้ว ไม่สามารถปฏิเสธได้")
    payment.status, payment.rejection_reason = "rejected", (reason or "สลิปไม่ถูกต้อง")[:255]
    payment.reviewed_at, payment.reviewed_by = timezone.now(), reviewed_by
    payment.save(update_fields=["status", "rejection_reason", "reviewed_at", "reviewed_by"])
    return payment
