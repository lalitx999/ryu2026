"""Student management for the custom admin: create, edit (incl. per-course entitlements), import."""
import datetime
import secrets
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from core.http import ServiceError
from courses.models import Course, Enrollment
from courses.services.access_service import AccessService
from users.models import User
from backoffice.services.course_admin_service import money, truthy

LIFETIME_DAYS = 999


def _dec(value, default=Decimal("0.00")):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return default


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _date(value):
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError:
        return None


def _grant(user, course, *, days=None, expires_at=None):
    """Activate one course for a user: fixed expiry date, N days, or lifetime (days >= 999)."""
    enr, _ = Enrollment.objects.get_or_create(user=user, course=course, defaults={"status": "ACTIVE", "is_active": True})
    enr.status, enr.is_active, enr.activated_at = "ACTIVE", True, timezone.now()
    if expires_at:
        enr.video_expires_at, enr.is_lifetime_video = expires_at, False
    elif days is not None:
        if days >= LIFETIME_DAYS:
            enr.is_lifetime_video = True
        else:
            enr.video_expires_at, enr.is_lifetime_video = timezone.localdate() + timedelta(days=days), False
    enr.save()


def _apply_entitlements(user, items):
    wanted = {_int(i.get("course_id"), None): i for i in items if isinstance(i, dict)}
    courses = {c.pk: c for c in Course.objects.filter(pk__in=[k for k in wanted if k])}
    existing = {e.course_id: e for e in Enrollment.objects.filter(user=user, course_id__in=courses)}
    for cid, item in wanted.items():
        course = courses.get(cid)
        if not course:
            continue
        enr = existing.get(cid) or Enrollment(user=user, course=course)
        active, lifetime = truthy(item.get("is_active", True)), truthy(item.get("is_lifetime", False))
        enr.is_active, enr.status, enr.is_lifetime_video = active, "ACTIVE" if active else "EXPIRED", lifetime
        if lifetime:
            enr.video_expires_at = None
        elif item.get("expires_at") and _date(item["expires_at"]):
            enr.video_expires_at = _date(item["expires_at"])
        enr.save()


@transaction.atomic
def create_user(data):
    email = str(data.get("email", "")).strip().lower()
    if not email:
        raise ServiceError("กรุณาระบุอีเมลผู้เรียน")
    if User.objects.filter(email=email).exists():
        raise ServiceError(f"อีเมล {email} นี้มีอยู่ในระบบเรียบร้อยแล้ว")
    password = str(data.get("password", "")).strip() or secrets.token_urlsafe(9)
    user = User.objects.create_user(
        email=email, password=password, name=str(data.get("name", "")).strip() or email, role="student",
        phone=str(data.get("phone", "")).strip(), nickname=str(data.get("nickname", "")).strip(),
        telegram_chat_id=str(data.get("telegram_chat_id", "")).strip(), total_spent=_dec(data.get("total_spent", 0)),
        points=_int(data.get("points", 0)), custom_renewal_price=money(data.get("custom_renewal_price")),
        admin_remark=str(data.get("admin_remark", "")).strip(), email_verified=True, force_password_change=True)
    AccessService.recalculate_lifetime_unlocks(user.id)
    course = Course.objects.filter(pk=data.get("course_id")).first() if data.get("course_id") else None
    if course:
        _grant(user, course, days=_int(data.get("duration_days", 30), None), expires_at=_date(data.get("expires_at")))
    return user, password


@transaction.atomic
def update_user(user_id, actor, data):
    user = User.objects.select_for_update().filter(pk=user_id).first()
    if not user:
        raise ServiceError("ไม่พบผู้ใช้", status=404)
    for f in ("name", "nickname", "phone", "telegram_chat_id", "admin_remark"):
        if f in data:
            setattr(user, f, str(data[f]).strip()[:2000])
    if data.get("email"):
        new = str(data["email"]).strip().lower()
        if new != user.email:
            if User.objects.filter(email=new).exclude(pk=user.pk).exists():
                raise ServiceError("อีเมลนี้ถูกใช้งานแล้ว")
            user.email = new
    if data.get("password"):
        if len(str(data["password"])) < 6:
            raise ServiceError("รหัสผ่านต้องยาวอย่างน้อย 6 ตัวอักษร")
        user.set_password(str(data["password"]))
    if "points" in data:
        user.points = _int(data["points"])
    if "total_spent" in data:
        user.total_spent = _dec(data["total_spent"], user.total_spent)
    if "custom_renewal_price" in data:
        user.custom_renewal_price = money(data["custom_renewal_price"])
    if data.get("role") in ("student", "admin"):
        if user.pk == actor.pk and data["role"] != "admin":
            raise ServiceError("ไม่สามารถลดสิทธิ์ตัวเองได้")
        user.role, user.is_staff = data["role"], data["role"] == "admin"
    if "is_active" in data:
        if user.pk == actor.pk and not truthy(data["is_active"]):
            raise ServiceError("ไม่สามารถระงับบัญชีตัวเองได้")
        user.is_active = truthy(data["is_active"])
    user.save()
    AccessService.recalculate_lifetime_unlocks(user.id)
    if isinstance(data.get("course_entitlements"), list):
        _apply_entitlements(user, data["course_entitlements"])
    return user


def import_students(rows):
    """Upsert students from parsed CSV rows.  Runs inside a Celery task (password hashing is slow)."""
    created = updated = 0
    errors = []
    emails = [str(r.get("email", "")).strip().lower() for r in rows if isinstance(r, dict)]
    existing = {u.email: u for u in User.objects.filter(email__in=emails)}
    courses_by_level = {}
    for c in Course.objects.filter(is_active=True):
        courses_by_level.setdefault(c.level, []).append(c)
    for idx, row in enumerate(rows, start=1):
        try:
            email = str(row.get("email", "")).strip().lower()
            if not email:
                errors.append(f"แถวที่ {idx}: ไม่พบอีเมลผู้เรียน")
                continue
            fields = dict(name=str(row.get("name") or email).strip(), phone=str(row.get("phone", "")).strip(),
                          nickname=str(row.get("nickname", "")).strip(), total_spent=_dec(row.get("total_spent", 0)),
                          points=_int(row.get("points", 0)), custom_renewal_price=money(row.get("custom_renewal_price")),
                          admin_remark=str(row.get("admin_remark") or "Imported from legacy system").strip())
            user = existing.get(email)
            with transaction.atomic():
                if user:
                    for k, v in fields.items():
                        if v not in ("", None) or k in ("custom_renewal_price", "total_spent", "points"):
                            setattr(user, k, v)
                    user.save()
                    updated += 1
                else:
                    password = str(row.get("password", "")).strip() or secrets.token_urlsafe(9)
                    user = User.objects.create_user(email=email, password=password, role="student", email_verified=True, **fields)
                    existing[email] = user
                    created += 1
                AccessService.recalculate_lifetime_unlocks(user.id)
                levels = row.get("lifetime_levels") or []
                if isinstance(levels, str):
                    levels = [x.strip().upper() for x in levels.split(",") if x.strip()]
                for lvl in levels:
                    for course in courses_by_level.get(lvl, []):
                        enr, _ = Enrollment.objects.get_or_create(user=user, course=course)
                        enr.is_active, enr.status, enr.is_lifetime_video = True, "ACTIVE", True
                        enr.save()
        except ServiceError as exc:
            errors.append(f"แถวที่ {idx} ({row.get('email', 'N/A')}): {exc.message}")
        except Exception as exc:  # one bad row must not abort the batch
            errors.append(f"แถวที่ {idx} ({row.get('email', 'N/A')}): {exc}")
    return {"imported_count": created, "updated_count": updated, "errors": errors[:50]}
