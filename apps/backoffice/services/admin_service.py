from core.http import ServiceError
from payments.services import payment_service
from users import tasks as user_tasks
from users.models import User


def review_payment(payment_id, reviewer, action, reason=""):
    if action == "approve":
        payment = payment_service.approve_payment(payment_id, reviewed_by=reviewer)
    elif action == "reject":
        payment = payment_service.reject_payment(payment_id, reviewer, reason)
    else:
        raise ServiceError("action ไม่ถูกต้อง")
    return payment


def broadcast(subject, message, target):
    """target: all | student | admin | active | expired | course_<id>  (all but `admin` reach students/users as before)."""
    from courses.models import Enrollment

    subject, message = str(subject or "").strip(), str(message or "").strip()
    if not subject or not message:
        raise ServiceError("กรุณาระบุหัวข้อและเนื้อหาของอีเมล")
    target = str(target or "all")
    qs = User.objects.filter(is_active=True)
    if target in ("student", "admin"):
        qs = qs.filter(role=target)
    elif target == "active":
        qs = qs.filter(role="student", id__in=Enrollment.objects.filter(is_active=True, status="ACTIVE").values("user_id"))
    elif target == "expired":
        qs = qs.filter(role="student", id__in=Enrollment.objects.filter(status="EXPIRED").values("user_id"))
    elif target.startswith("course_") and target[7:].isdigit():
        qs = qs.filter(role="student", id__in=Enrollment.objects.filter(course_id=int(target[7:]), is_active=True).values("user_id"))
    recipients = list(qs.values_list("email", flat=True).distinct())
    if not recipients:
        raise ServiceError("ไม่พบรายชื่ออีเมลผู้ใช้งานที่ตรงตามเงื่อนไข")
    user_tasks.send_broadcast_email.delay(subject, message, recipients)  # sent in the background
    return len(recipients)
