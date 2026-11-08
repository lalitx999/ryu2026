"""Read side of the operational screens: moderation, tickets, migrations, slip rules, settings, renewals."""
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone

from community.models import Comment, Post
from courses.services import reminder_service
from payments.models import Payment, SlipBlacklistPattern, SlipVerificationLog
from support.models import SupportTicket
from system_config.models import LifetimeStudentImport, MigrationRequest, SystemSetting

PAGE = 20
MOD_STATUSES = ("PENDING", "REWRITTEN", "REJECTED", "APPROVED")


def payment_detail(payment_id):
    p = Payment.objects.select_related("user", "course").filter(pk=payment_id).first()
    if not p:
        return None
    log = SlipVerificationLog.objects.filter(payment=p).order_by("-verified_at").first()
    return {
        "id": p.id, "status": p.status, "amount": str(p.amount), "duration_days": p.duration_days, "level_access": p.level_access or "",
        "is_zoom_included": p.is_zoom_included, "is_renewal": p.is_renewal, "trans_ref": p.trans_ref or "", "note": p.note or "",
        "rejection_reason": p.rejection_reason or "", "has_slip": bool(p.slip_path),
        "submitted_at": timezone.localtime(p.submitted_at).strftime("%d/%m/%Y %H:%M"),
        "reviewed_at": timezone.localtime(p.reviewed_at).strftime("%d/%m/%Y %H:%M") if p.reviewed_at else "",
        "user": {"id": p.user_id, "name": p.user.name or p.user.email, "email": p.user.email, "phone": p.user.phone or "",
                 "total_spent": str(p.user.total_spent)},
        "course": {"id": p.course_id, "title": p.course.title, "price": str(p.course.price)},
        "easyslip": None if not log else {
            "status": log.get_status_display(), "amount": str(log.verified_amount) if log.verified_amount is not None else "",
            "bank": log.verified_bank or "", "account": log.verified_account or "", "error": log.error_message or "",
            "at": timezone.localtime(log.verified_at).strftime("%d/%m/%Y %H:%M")},
    }


def community_page(kind, status, page):
    model = Comment if kind == "comments" else Post
    qs = model.objects.select_related("user").order_by("-created_at")
    if status in MOD_STATUSES:
        qs = qs.filter(moderation_status=status)
    counts = dict(model.objects.values_list("moderation_status").annotate(n=Count("id")))
    return Paginator(qs, PAGE).get_page(page), counts


def tickets_page(status, page):
    qs = SupportTicket.objects.select_related("user").order_by("-created_at")
    if status in ("pending", "resolved"):
        qs = qs.filter(status=status)
    counts = dict(SupportTicket.objects.values_list("status").annotate(n=Count("id")))
    return Paginator(qs, PAGE).get_page(page), counts


def migrations_page(status, page):
    qs = MigrationRequest.objects.order_by("-created_at")
    if status in ("pending", "processing", "approved", "rejected"):
        qs = qs.filter(status=status)
    counts = dict(MigrationRequest.objects.values_list("status").annotate(n=Count("id")))
    return Paginator(qs, PAGE).get_page(page), counts


def lifetime_imports_page(page, q=""):
    qs = LifetimeStudentImport.objects.order_by("-created_at")
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(invite_code__icontains=q))
    stats = LifetimeStudentImport.objects.aggregate(total=Count("id"), registered=Count("id", filter=Q(is_registered=True)))
    return Paginator(qs, PAGE).get_page(page), stats


def slip_rules():
    return list(SlipBlacklistPattern.objects.order_by("type", "pattern"))


def verification_logs(page):
    qs = SlipVerificationLog.objects.select_related("user", "payment").only(
        "id", "status", "verified_amount", "verified_bank", "verified_account", "error_message", "verified_at",
        "user__email", "payment__id", "payment__amount").order_by("-verified_at")
    return Paginator(qs, PAGE).get_page(page)


def settings_rows():
    """Values are never returned (they can hold secrets): only the key and how long the value is."""
    return [{"key": s.key_name, "length": len(s.key_value or "")} for s in SystemSetting.objects.order_by("key_name")]


def renewals(window=7):
    today = timezone.localdate()
    rows = []
    for e in reminder_service.expiring_list(window, today):
        rows.append({"id": e.id, "email": e.user.email, "name": e.user.name, "course": e.course.title,
                     "expires": e.video_expires_at, "days": (e.video_expires_at - today).days})
    return rows
