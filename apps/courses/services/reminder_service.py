"""Course renewal reminders: who is due, and the email itself."""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from courses.models import Enrollment

logger = logging.getLogger(__name__)
DEFAULT_DAYS = (3, 2, 1)
EXPIRED_WINDOW = 30  # days after expiry that "include expired" still reaches


def due_enrollments(days=DEFAULT_DAYS, include_expired=False, today=None):
    """Enrollments whose expiry is exactly N days away (or recently expired), filtered in the DB."""
    today = today or timezone.localdate()
    targets = [today + timedelta(days=int(d)) for d in days]
    cond_dates = {"video_expires_at__in": targets}
    qs = Enrollment.objects.filter(is_lifetime_video=False, user__is_active=True).select_related("user", "course")
    if include_expired:
        from django.db.models import Q
        return qs.filter(Q(**cond_dates) | Q(video_expires_at__gte=today - timedelta(days=EXPIRED_WINDOW), video_expires_at__lt=today))
    return qs.filter(**cond_dates)


def expiring_list(window=7, today=None):
    """For the admin screen: expiring within `window` days, plus expired in the last 30 days."""
    today = today or timezone.localdate()
    return (Enrollment.objects.filter(is_lifetime_video=False, user__is_active=True, video_expires_at__isnull=False,
                                      video_expires_at__gte=today - timedelta(days=EXPIRED_WINDOW),
                                      video_expires_at__lte=today + timedelta(days=window))
            .select_related("user", "course").order_by("video_expires_at"))


def _copy(days_remaining, course, expiry):
    if days_remaining is not None and days_remaining < 0:
        return ("⏰ สิทธิ์เข้าเรียนคอร์สของคุณหมดอายุแล้ว", f"สิทธิ์เข้าเรียนคอร์ส {course} หมดอายุเมื่อวันที่ {expiry}", "#ef4444", "EXPIRED / หมดอายุ")
    if days_remaining == 0:
        return ("⚠️ สิทธิ์เข้าเรียนคอร์สของคุณหมดอายุวันนี้!", f"สิทธิ์เข้าเรียนคอร์ส {course} จะหมดอายุในวันนี้ ({expiry})", "#f59e0b", "EXPIRES TODAY / หมดอายุวันนี้")
    d = f"{days_remaining} วัน" if days_remaining is not None else ""
    return (f"⏳ แจ้งเตือน: สิทธิ์เรียนคอร์สของคุณจะหมดอายุในอีก {d}",
            f"สิทธิ์เข้าเรียนคอร์ส {course} กำลังจะหมดอายุในวันที่ {expiry} (เหลือเวลาอีก {d})", "#3b82f6", f"REMAINING {d} / เหลือเวลาอีก {d}")


def send_reminder(enrollment, days_remaining=None, *, dedupe=True):
    """Send one reminder.  Returns True on success; skips (True) if the same one already went out today."""
    user = enrollment.user
    if not user or not user.email or not enrollment.video_expires_at:
        logger.warning("enrollment %s has no email/expiry", enrollment.id)
        return False
    today = timezone.localdate()
    if days_remaining is None:
        days_remaining = (enrollment.video_expires_at - today).days
    key = f"renewal-sent:{enrollment.id}:{today.isoformat()}"
    if dedupe and cache.get(key):
        return True
    expiry = enrollment.video_expires_at.strftime("%d/%m/%Y")
    headline, status_sub, color, badge = _copy(days_remaining, enrollment.course.title, expiry)
    ctx = {"subject": f"[RyuClass] แจ้งเตือนต่ออายุคอร์สเรียน: {enrollment.course.title}", "headline": headline, "status_sub": status_sub,
           "badge_color": color, "badge_text": badge, "user_name": user.name or user.email.split("@")[0],
           "course_title": enrollment.course.title, "email": user.email, "expiry": expiry,
           "cta_url": f"{settings.SITE_URL.rstrip('/')}/courses/{enrollment.course_id}/"}
    try:
        msg = EmailMultiAlternatives(ctx["subject"], render_to_string("emails/renewal_reminder.txt", ctx),
                                     settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(render_to_string("emails/renewal_reminder.html", ctx), "text/html")
        msg.send()
    except Exception as exc:
        logger.warning("reminder to %s failed: %s", user.email, exc)
        return False
    cache.set(key, 1, 86400)
    return True
