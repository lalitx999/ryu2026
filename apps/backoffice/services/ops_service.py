"""Operational admin actions.  Every state change goes through a whitelist, never a free-form field name."""
from django.db import transaction
from django.utils import timezone

from community.models import Comment, Post
from core.http import ServiceError
from courses import tasks as course_tasks
from courses.models import Enrollment
from payments.models import SlipBlacklistPattern
from support.models import SupportTicket
from system_config.models import MigrationRequest, SystemSetting

KINDS = {"posts": Post, "comments": Comment}
MOD_ACTIONS = {"approve": "APPROVED", "reject": "REJECTED"}
TICKET_ACTIONS = {"resolve": "resolved", "reopen": "pending"}
MIGRATION_ACTIONS = {"processing": "processing", "approve": "approved", "reject": "rejected", "reopen": "pending"}
RULE_TYPES = {"bank", "amount", "name", "keyword"}


def moderate(kind, pk, action):
    model = KINDS.get(kind)
    if not model:
        raise ServiceError("ไม่รู้จักประเภทเนื้อหา")
    if action == "delete":
        deleted, _ = model.objects.filter(pk=pk).delete()
        if not deleted:
            raise ServiceError("ไม่พบรายการ", status=404)
        return "ลบเรียบร้อยแล้ว"
    if action not in MOD_ACTIONS:
        raise ServiceError("action ไม่ถูกต้อง")
    if not model.objects.filter(pk=pk).update(moderation_status=MOD_ACTIONS[action]):
        raise ServiceError("ไม่พบรายการ", status=404)
    return "อนุมัติแล้ว" if action == "approve" else "ปฏิเสธ/ซ่อนแล้ว"


def ticket_action(pk, action):
    if action not in TICKET_ACTIONS:
        raise ServiceError("action ไม่ถูกต้อง")
    if not SupportTicket.objects.filter(pk=pk).update(status=TICKET_ACTIONS[action]):
        raise ServiceError("ไม่พบคำร้อง", status=404)


@transaction.atomic
def migration_action(pk, action, admin, note=""):
    if action not in MIGRATION_ACTIONS:
        raise ServiceError("action ไม่ถูกต้อง")
    req = MigrationRequest.objects.select_for_update().filter(pk=pk).first()
    if not req:
        raise ServiceError("ไม่พบคำขอ", status=404)
    req.status = MIGRATION_ACTIONS[action]
    req.admin_note = str(note or "")[:2000] or req.admin_note
    done = req.status in ("approved", "rejected")
    req.processed_at, req.processed_by = (timezone.now(), admin.pk) if done else (None, None)
    req.save()


def add_rule(rule_type, pattern, description=""):
    pattern = str(pattern or "").strip()
    if rule_type not in RULE_TYPES or not pattern:
        raise ServiceError("กรุณาระบุประเภทและรูปแบบที่ต้องการ")
    if SlipBlacklistPattern.objects.filter(type=rule_type, pattern__iexact=pattern).exists():
        raise ServiceError("มีกฎนี้อยู่แล้ว")
    return SlipBlacklistPattern.objects.create(type=rule_type, pattern=pattern[:255], description=str(description or "")[:1000])


def delete_rule(pk):
    deleted, _ = SlipBlacklistPattern.objects.filter(pk=pk).delete()
    if not deleted:
        raise ServiceError("ไม่พบกฎนี้", status=404)


def save_setting(user, key, value):
    if not user.is_superuser:
        raise ServiceError("เฉพาะ Super Admin เท่านั้น", status=403)
    key = str(key or "").strip()
    if not key or len(key) > 100 or not key.replace("_", "").replace(".", "").replace("-", "").isalnum():
        raise ServiceError("ชื่อคีย์ใช้ได้เฉพาะตัวอักษร ตัวเลข _ . -")
    SystemSetting.objects.update_or_create(key_name=key, defaults={"key_value": str(value or "")})


def delete_setting(user, key):
    if not user.is_superuser:
        raise ServiceError("เฉพาะ Super Admin เท่านั้น", status=403)
    SystemSetting.objects.filter(key_name=key).delete()


def send_renewals(data):
    """Queue reminders: either explicit enrollment ids, or everything due in `days` (default 3/2/1)."""
    ids = data.get("enrollment_ids")
    if ids:
        if not isinstance(ids, list) or len(ids) > 500:
            raise ServiceError("รายการไม่ถูกต้อง (สูงสุด 500)")
        ids = [int(i) for i in ids if str(i).isdigit()]
        if not Enrollment.objects.filter(pk__in=ids, is_lifetime_video=False).exists():
            raise ServiceError("ไม่พบรายการที่ส่งได้ (สิทธิ์ตลอดชีพไม่ต้องเตือน)")
        return course_tasks.send_reminders_for.delay(ids)
    days = data.get("days")
    days = [int(d) for d in days if str(d).lstrip("-").isdigit()] if isinstance(days, list) else None
    return course_tasks.send_renewal_reminders.delay(days, bool(data.get("include_expired")))
