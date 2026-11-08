"""Aggregations for the custom admin.  Everything is a DB-side aggregate or a paginated slice."""
from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from courses.models import Course, Enrollment
from payments.models import Payment
from support.models import SupportTicket
from users.models import User

PAGE_SIZE = 20
PAGE_SIZES = (10, 20, 50, 100)


def page_size(value):
    """Only the sizes the screens offer are accepted (a huge per_page would defeat pagination)."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return PAGE_SIZE
    return n if n in PAGE_SIZES else PAGE_SIZE


def dashboard(days=7):
    since = timezone.now() - timedelta(days=days - 1)
    approved = Payment.objects.filter(status="approved")
    daily = dict(approved.filter(reviewed_at__gte=since.replace(hour=0, minute=0, second=0, microsecond=0))
                 .annotate(d=TruncDate("reviewed_at")).values_list("d").annotate(total=Sum("amount")))
    labels, amounts = [], []
    for i in range(days):
        day = (timezone.localdate() - timedelta(days=days - 1 - i))
        labels.append(day.strftime("%d/%m"))
        amounts.append(float(daily.get(day, 0) or 0))
    peak = max(amounts) or 1
    bars = [{"label": l, "amount": a, "pct": max(2, round(a / peak * 100)) if a else 2} for l, a in zip(labels, amounts)]
    totals = approved.aggregate(rev=Coalesce(Sum("amount"), Value(0), output_field=DecimalField()))
    return {
        "cards": {
            "pending_payments": Payment.objects.filter(status="pending").count(),
            "active_courses": Course.objects.filter(is_active=True).count(),
            "total_students": User.objects.filter(role="student").count(),
            "pending_tickets": SupportTicket.objects.filter(status="pending").count(),
            "total_revenue": float(totals["rev"]),
        },
        "sales": {"bars": bars, "period_revenue": sum(amounts)},
        "top_courses": list(approved.values("course__title").annotate(total=Sum("amount")).order_by("-total")[:5]),
        "recent_payments": Payment.objects.select_related("user", "course").only(
            "id", "amount", "status", "submitted_at", "user__name", "user__email", "course__title")
        .order_by("-submitted_at")[:8],
    }


def payments_page(status="", q="", page=1, per_page=PAGE_SIZE):
    qs = Payment.objects.select_related("user", "course").only(
        "id", "amount", "duration_days", "status", "slip_path", "submitted_at", "rejection_reason", "is_renewal",
        "user__name", "user__email", "user__phone", "course__title", "course__level").order_by("-submitted_at")
    if status in ("pending", "approved", "rejected"):
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(user__email__icontains=q) | Q(user__name__icontains=q) | Q(user__phone__icontains=q))
    counts = Payment.objects.aggregate(
        pending=Count("id", filter=Q(status="pending")), approved=Count("id", filter=Q(status="approved")),
        rejected=Count("id", filter=Q(status="rejected")))
    return Paginator(qs, per_page).get_page(page), counts


def users_page(q="", role="", page=1, per_page=PAGE_SIZE):
    qs = User.objects.annotate(
        active_courses=Count("enrollments", filter=Q(enrollments__is_active=True), distinct=True)
    ).only("id", "name", "email", "phone", "role", "total_spent", "is_active", "created_at", "admin_remark",
           "custom_renewal_price").order_by("-created_at")
    if role in ("student", "admin"):
        qs = qs.filter(role=role)
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(name__icontains=q) | Q(phone__icontains=q) | Q(nickname__icontains=q))
    return Paginator(qs, per_page).get_page(page)


def courses_list():
    return list(Course.objects.annotate(
        lessons_count=Count("lessons", distinct=True),
        students=Count("enrollments", filter=Q(enrollments__is_active=True), distinct=True),
    ).order_by("sort_order", "id"))


# ───────────────────────── detail loaders ─────────────────────────
def course_detail(course_id):
    """Course with its modules and lessons: 3 queries however large the course is."""
    from django.db.models import Prefetch

    from courses.models import Lesson, Module

    lessons = Lesson.objects.filter(is_active=True).only(
        "id", "module_id", "title", "description", "video_url", "duration", "pdf_file", "pdf_title", "is_free", "sort_order"
    ).order_by("sort_order", "id")
    course = Course.objects.filter(pk=course_id).prefetch_related(
        Prefetch("modules", queryset=Module.objects.filter(is_active=True).order_by("sort_order", "id")
                 .prefetch_related(Prefetch("lessons", queryset=lessons)))).first()
    return course


def user_detail(user_id):
    """Everything the edit dialog needs (profile, tier, one row per course with the student's access)."""
    from courses.models import Enrollment
    from courses.services.access_service import AccessService

    u = User.objects.filter(pk=user_id).first()
    if not u:
        return None
    enrollments = {e.course_id: e for e in Enrollment.objects.filter(user=u)}
    access = []
    for c in Course.objects.only("id", "title", "level").order_by("sort_order", "id"):
        e = enrollments.get(c.id)
        access.append({"course_id": c.id, "course_title": c.title, "level": c.level,
                       "is_active": bool(e and e.is_active), "is_lifetime": bool(e and e.is_lifetime_video),
                       "expires_at": e.video_expires_at.isoformat() if e and e.video_expires_at else ""})
    return {"id": u.id, "name": u.name, "email": u.email, "nickname": u.nickname or "", "phone": u.phone or "",
            "telegram_chat_id": u.telegram_chat_id or "", "total_spent": str(u.total_spent), "points": u.points,
            "custom_renewal_price": str(u.custom_renewal_price) if u.custom_renewal_price is not None else "",
            "admin_remark": u.admin_remark or "", "role": u.role, "is_active": u.is_active,
            "tier": AccessService.get_tier_progress(u.total_spent).get("current_level", "เริ่มต้น"), "access": access}


# ───────────────────────── reports ─────────────────────────
REVENUE_TARGET = 100_000  # same fixed goal the original sales page used


def sales_report(months=12):
    from django.db.models.functions import TruncMonth

    approved = Payment.objects.filter(status="approved")
    now = timezone.localtime()
    idx = now.year * 12 + (now.month - 1) - (months - 1)          # calendar-month arithmetic (no 30/31-day drift)
    y, m = divmod(idx, 12)
    m += 1
    first = now.replace(year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0)
    by_month = dict(approved.filter(reviewed_at__gte=first).annotate(m=TruncMonth("reviewed_at"))
                    .values_list("m").annotate(t=Sum("amount")))
    series = []
    for _ in range(months):
        key = next((k for k in by_month if k.year == y and k.month == m), None)
        series.append({"label": f"{m:02d}/{str(y)[2:]}", "amount": float(by_month.get(key, 0) or 0)})
        m += 1
        if m > 12:
            y, m = y + 1, 1
    peak = max((s["amount"] for s in series), default=0) or 1
    for s in series:
        s["pct"] = max(2, round(s["amount"] / peak * 100)) if s["amount"] else 2
    totals = approved.aggregate(
        revenue=Coalesce(Sum("amount"), Value(0), output_field=DecimalField()), count=Count("id"),
        renewal=Coalesce(Sum("amount", filter=Q(is_renewal=True)), Value(0), output_field=DecimalField()),
        renewal_n=Count("id", filter=Q(is_renewal=True)))
    revenue = float(totals["revenue"])
    packages = list(approved.values("duration_days").annotate(n=Count("id"), total=Sum("amount")).order_by("-total"))
    return {"series": series, "revenue": revenue, "count": totals["count"], "renewal": float(totals["renewal"]),
            "renewal_n": totals["renewal_n"], "new": revenue - float(totals["renewal"]),
            "avg": revenue / totals["count"] if totals["count"] else 0, "target": REVENUE_TARGET,
            "target_pct": min(100, round(revenue / REVENUE_TARGET * 100)), "packages": packages,
            "top_courses": list(approved.values("course__title").annotate(n=Count("id"), total=Sum("amount")).order_by("-total")[:8])}


def analytics():
    """Real engagement numbers (the legacy page showed hard-coded demo figures)."""
    from courses.models import Lesson, Progress, StudyActivityLog
    from quizzes.models import QuizAttempt

    today = timezone.localdate()
    week = today - timedelta(days=6)
    logs = StudyActivityLog.objects.aggregate(
        minutes=Coalesce(Sum("minutes_spent"), Value(0)), done=Coalesce(Sum("lessons_completed"), Value(0)))
    dau_today = StudyActivityLog.objects.filter(date=today).values("user").distinct().count()
    dau_week = StudyActivityLog.objects.filter(date__gte=week).values("user").distinct().count()
    attempts = QuizAttempt.objects.aggregate(n=Count("id"), total_q=Coalesce(Sum("total_questions"), Value(0)),
                                             score=Coalesce(Sum("score"), Value(0)))
    pass_n = QuizAttempt.objects.filter(total_questions__gt=0, score__gte=F("total_questions") * 0.6).count()  # DB-side
    completed = Progress.objects.filter(is_completed=True)
    per_course = []
    for c in Course.objects.filter(is_active=True).annotate(
            lessons_n=Count("lessons", filter=Q(lessons__is_active=True), distinct=True),
            learners=Count("enrollments", filter=Q(enrollments__is_active=True), distinct=True)).order_by("sort_order", "id"):
        done = completed.filter(lesson__course_id=c.id).count()
        denom = c.lessons_n * c.learners
        per_course.append({"title": c.title, "level": c.level, "learners": c.learners, "lessons": c.lessons_n,
                           "pct": min(100, round(done / denom * 100)) if denom else 0})
    return {"metrics": [
        {"label": "บทเรียนที่เรียนจบ (ครั้ง)", "value": f"{completed.count():,}", "icon": "✅"},
        {"label": "อัตราสอบผ่าน Quiz (≥60%)", "value": f"{(pass_n / attempts['n'] * 100):.1f}%" if attempts["n"] else "-", "icon": "📝"},
        {"label": "นาทีเรียนสะสมทั้งหมด", "value": f"{logs['minutes']:,}", "icon": "⏱️"},
        {"label": "ผู้เรียนที่ใช้งานวันนี้ (DAU)", "value": f"{dau_today:,}", "icon": "👥"},
        {"label": "ผู้เรียนที่ใช้งาน 7 วัน", "value": f"{dau_week:,}", "icon": "📅"},
        {"label": "จำนวนครั้งที่ทำ Quiz", "value": f"{attempts['n']:,}", "icon": "🧠"},
    ], "per_course": per_course, "lessons_total": Lesson.objects.filter(is_active=True).count()}


def roles_overview():
    admins = list(User.objects.filter(role="admin").only("id", "name", "email", "is_active", "is_superuser", "created_at").order_by("id"))
    counts = User.objects.aggregate(students=Count("id", filter=Q(role="student")), admins=Count("id", filter=Q(role="admin")),
                                    suspended=Count("id", filter=Q(is_active=False)))
    return {"admins": admins, "counts": counts}


def payments_csv_rows():
    """Streamed straight from the DB cursor, so the export never holds the whole table in memory."""
    qs = (Payment.objects.select_related("user", "course").order_by("-submitted_at")
          .only("id", "amount", "duration_days", "status", "is_renewal", "submitted_at", "reviewed_at", "trans_ref",
                "user__email", "user__name", "course__title"))
    for p in qs.iterator(chunk_size=500):
        yield [p.id, p.user.email, p.user.name, p.course.title, p.duration_days, p.amount, p.status,
               "renewal" if p.is_renewal else "new", p.trans_ref or "",
               timezone.localtime(p.submitted_at).strftime("%Y-%m-%d %H:%M"),
               timezone.localtime(p.reviewed_at).strftime("%Y-%m-%d %H:%M") if p.reviewed_at else ""]
