"""Authentication / registration use-cases.  Views only parse input and call these."""
import re
import secrets
from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from core.http import ServiceError, is_admin_user
from courses.models import Course
from payments.services import payment_service
from users.models import EmailVerificationCode, User
from users import tasks

VERIFICATION_CODE_TTL_MINUTES = 10
VERIFICATION_RESEND_WAIT_SECONDS = 60
VERIFICATION_MAX_ATTEMPTS = 5
RESET_MAX_ATTEMPTS = 5  # per email / 15 min - the reset form only needs email + phone, so throttle it

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean_email(value):
    email = str(value or "").strip().lower()
    if not EMAIL_RE.match(email):
        raise ServiceError("รูปแบบอีเมลไม่ถูกต้อง")
    return email


def issue_verification_code(user):
    """Invalidate older challenges, store only a hash, email the plain code via Celery."""
    now = timezone.now()
    EmailVerificationCode.objects.filter(user=user, verified_at__isnull=True).update(expires_at=now)
    code = f"{secrets.randbelow(1_000_000):06d}"
    EmailVerificationCode.objects.create(
        user=user, code_hash=make_password(code), expires_at=now + timedelta(minutes=VERIFICATION_CODE_TTL_MINUTES)
    )
    tasks.send_verification_email.delay(user.email, user.name, code, VERIFICATION_CODE_TTL_MINUTES)


def login_user(email, password):
    email = str(email or "").strip()
    if not email or not password:
        raise ServiceError("กรุณากรอกอีเมลและรหัสผ่านให้ครบถ้วนครับ")
    candidate = User.objects.filter(email__iexact=email).first()
    user = authenticate(email=email, password=password)
    if user is None:
        if candidate and candidate.check_password(password) and not candidate.is_active:
            raise ServiceError("บัญชีผู้ใช้นี้ถูกระงับการใช้งาน")
        raise ServiceError("อีเมลหรือรหัสผ่านไม่ถูกต้องครับ")
    if not is_admin_user(user) and not user.email_verified:
        if EmailVerificationCode.objects.filter(user=user, verified_at__isnull=True).exists():
            raise ServiceError("กรุณายืนยันอีเมลด้วยรหัส 6 หลักก่อนเข้าสู่ระบบ", status=403, verification_required=True)
    return user


@transaction.atomic
def register_student(data, slip_file):
    required = ("name", "email", "password", "phone", "level", "duration")
    if any(not str(data.get(k, "")).strip() for k in required) or not slip_file:
        raise ServiceError("กรุณากรอกข้อมูลและแนบสลิปการโอนเงินให้ครบถ้วนทุกช่องครับ")
    email = _clean_email(data["email"])
    if len(str(data["password"])) < 6:
        raise ServiceError("รหัสผ่านต้องยาวอย่างน้อย 6 ตัวอักษร")
    if User.objects.filter(email__iexact=email).exists():
        raise ServiceError("อีเมลนี้ถูกใช้งานสมัครเรียนแล้ว หากต้องการเรียนเพิ่มหรือต่ออายุ กรุณาเข้าสู่ระบบก่อนครับ")

    course = Course.objects.filter(level=data["level"], is_active=True).order_by("id").first()
    if course is None:
        raise ServiceError("ระดับคอร์สไม่ถูกต้อง")
    try:
        duration = int(data["duration"])
    except (TypeError, ValueError):
        raise ServiceError("ระยะเวลาเรียนไม่ถูกต้อง")
    # Price is validated *before* an account or a slip is stored.
    amount = payment_service.expected_amount(course, duration, data.get("expected_amount"))

    user = User.objects.create_user(
        email=email, password=data["password"], name=str(data["name"]).strip(),
        nickname=str(data.get("nickname", "")).strip() or None, phone=str(data["phone"]).strip(), role="student",
    )
    payment_service.submit_slip_payment(
        user=user, course=course, amount=amount, duration_days=duration,
        slip_file=slip_file, is_zoom_included=duration >= 180, is_renewal=False,
    )
    issue_verification_code(user)
    return user


def verify_email(email, code):
    email, code = str(email or "").strip().lower(), str(code or "").strip()
    if not email or not code.isdigit() or len(code) != 6:
        raise ServiceError("กรุณากรอกอีเมลและรหัสยืนยัน 6 หลักให้ครบถ้วน")
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        raise ServiceError("รหัสยืนยันไม่ถูกต้องหรือหมดอายุ")
    challenge = EmailVerificationCode.objects.filter(user=user, verified_at__isnull=True).first()
    if not challenge or challenge.expires_at <= timezone.now():
        raise ServiceError("รหัสยืนยันหมดอายุ กรุณาขอรหัสใหม่")
    if challenge.attempts >= VERIFICATION_MAX_ATTEMPTS:
        raise ServiceError("กรอกรหัสผิดเกินกำหนด กรุณาขอรหัสใหม่", status=429)
    challenge.attempts += 1
    if not check_password(code, challenge.code_hash):
        challenge.save(update_fields=["attempts"])
        raise ServiceError("รหัสยืนยันไม่ถูกต้อง")
    challenge.verified_at = timezone.now()
    challenge.save(update_fields=["attempts", "verified_at"])
    User.objects.filter(pk=user.pk).update(email_verified=True)
    user.email_verified = True
    tasks.send_welcome_email.delay(user.email)
    return user


def resend_verification(email):
    user = User.objects.filter(email__iexact=str(email or "").strip()).first()
    if not user or user.email_verified:
        return  # same answer either way: don't leak which emails exist
    latest = EmailVerificationCode.objects.filter(user=user, verified_at__isnull=True).first()
    if latest and (timezone.now() - latest.sent_at).total_seconds() < VERIFICATION_RESEND_WAIT_SECONDS:
        raise ServiceError("กรุณารอ 1 นาทีก่อนขอรหัสใหม่", status=429)
    issue_verification_code(user)


def reset_password(email, phone, new_password):
    email, phone, new_password = str(email or "").strip(), str(phone or "").strip(), str(new_password or "").strip()
    if not email or not new_password:
        raise ServiceError("กรุณาระบุอีเมลและรหัสผ่านใหม่")
    if len(new_password) < 6:
        raise ServiceError("รหัสผ่านต้องยาวอย่างน้อย 6 ตัวอักษร")
    key = f"pwreset:{email.lower()}"
    tries = cache.get(key, 0)
    if tries >= RESET_MAX_ATTEMPTS:
        raise ServiceError("ลองบ่อยเกินไป กรุณารอ 15 นาทีแล้วลองใหม่", status=429)
    cache.set(key, tries + 1, 15 * 60)
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        raise ServiceError("ไม่พบอีเมลสมาชิกนี้ในระบบ", status=404)
    if not phone or not user.phone or user.phone.replace("-", "") != phone.replace("-", ""):
        raise ServiceError("เบอร์โทรศัพท์ไม่ตรงกับข้อมูลในระบบ")
    user.set_password(new_password)
    user.save(update_fields=["password"])
    cache.delete(key)


def update_profile(user, data):
    fields = []
    for attr in ("name", "nickname", "phone"):
        value = str(data.get(attr, "") or "").strip()
        if value:
            setattr(user, attr, value)
            fields.append(attr)
    password = str(data.get("password", "") or "").strip()
    if password:
        if len(password) < 6:
            raise ServiceError("รหัสผ่านต้องยาวอย่างน้อย 6 ตัวอักษร")
        user.set_password(password)
        fields.append("password")
    if fields:
        user.save(update_fields=fields)
    return user
