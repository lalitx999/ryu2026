"""Read-side queries.  Every function here is O(1) in the number of courses/lessons (no N+1)."""
import os
from urllib.parse import quote

from django.db.models import Count, Q
from django.utils import timezone

from courses.models import Course, Enrollment, Lesson, Module, Progress
from courses.pricing import package_prices
from courses.services.access_service import AccessService
from courses.services.video import decrypt_video_url, to_embed_url


def catalog(user=None):
    """Course cards for the desktop / profile.  3 queries total regardless of catalogue size."""
    courses = list(
        Course.objects.filter(is_active=True).order_by("sort_order", "id")
        .annotate(total_lessons=Count("lessons", filter=Q(lessons__is_active=True), distinct=True))
        .only("id", "level", "title", "description", "price", "price_180", "price_365", "price_lifetime", "thumbnail")
    )
    done, enrollments, rank, active, today = {}, {}, 0, [], timezone.localdate()
    if user is not None and user.is_authenticated:
        done = dict(
            Progress.objects.filter(user=user, is_completed=True, lesson__course__in=courses)
            .values_list("lesson__course_id").annotate(n=Count("id")))
        active = list(Enrollment.objects.filter(user=user, is_active=True).select_related("course")
                      .only("course_id", "status", "is_lifetime_video", "video_expires_at", "course__level"))
        enrollments = {e.course_id: e for e in active}
        rank = AccessService.video_rank_for(active)
    result = []
    custom = getattr(user, "custom_renewal_price", None) if user is not None and getattr(user, "is_authenticated", False) else None
    renewal_price = str(custom) if custom else None  # admin-set per-student renewal price (None = package price)
    for c in courses:
        completed = done.get(c.id, 0)
        enrollment = enrollments.get(c.id)
        window = AccessService.access_window(active, c.level, today) if active else None
        result.append({
            "id": c.id, "level": c.level, "title": c.title, "description": c.description or "",
            "price": str(c.price), "packages": package_prices(c), "thumbnail": c.thumbnail or "",
            "renewal_price": renewal_price,
            "has_access": rank >= AccessService.LEVEL_RANK.get(c.level, 99) > 0,
            "is_lifetime": bool(enrollment and enrollment.is_lifetime_video),
            "expires_at": enrollment.video_expires_at if enrollment else None,
            # what the student actually has for this level (own enrollment or a higher tier that covers it)
            "access_lifetime": bool(window and window[0]), "access_until": window[1] if window else None,
            "days_left": window[2] if window else None,
            "total_lessons": c.total_lessons, "completed_lessons": completed,
            "progress_percent": int(completed / c.total_lessons * 100) if c.total_lessons else 0,
        })
    return result


def course_outline(course_id, user=None):
    """Modules + lessons + progress for one course in 4 queries; video URLs only if entitled/free."""
    course = Course.objects.filter(id=course_id, is_active=True).first()
    if course is None:
        return None
    has_access = bool(user and user.is_authenticated and AccessService.has_video_access(user.id, course.level))
    lessons = list(
        Lesson.objects.filter(course=course, is_active=True, module__is_active=True)
        .order_by("sort_order", "id")
        .only("id", "module_id", "title", "description", "video_url", "duration", "pdf_file", "pdf_title", "is_free"))
    progress = {}
    if user and user.is_authenticated and lessons:
        progress = {p.lesson_id: p for p in Progress.objects.filter(user=user, lesson__in=lessons)
                    .only("lesson_id", "video_time", "is_completed")}
    by_module = {}
    for lesson in lessons:
        entitled = has_access or lesson.is_free
        p = progress.get(lesson.id)
        pdf_url = None
        if entitled and lesson.pdf_file:
            pdf_url = f"/storage/protected_pdfs/{quote(os.path.basename(str(lesson.pdf_file.name)))}"
        by_module.setdefault(lesson.module_id, []).append({
            "id": lesson.id, "title": lesson.title, "description": lesson.description or "",
            "duration_seconds": lesson.duration, "is_free": lesson.is_free,
            "video_time": p.video_time if p else 0, "is_completed": bool(p and p.is_completed),
            "video_url": to_embed_url(decrypt_video_url(lesson.video_url)) if entitled else None,
            "pdf_url": pdf_url, "pdf_title": lesson.pdf_title or "เอกสารประกอบการเรียน (PDF)",
            "locked": not entitled,
        })
    modules = Module.objects.filter(course=course, is_active=True).order_by("sort_order", "id").only("id", "title")
    return {
        "course_id": course.id, "level": course.level, "course_title": course.title,
        "course_description": course.description or "", "has_access": has_access,
        "price": str(course.price), "packages": package_prices(course), "thumbnail": course.thumbnail or "",
        "modules": [{"id": m.id, "title": m.title, "lessons": by_module.get(m.id, [])} for m in modules],
    }


def free_trial_lessons():
    qs = (Lesson.objects.filter(is_free=True, is_active=True, course__is_active=True)
          .select_related("course", "module").order_by("course__sort_order", "sort_order", "id")
          .only("id", "title", "description", "duration", "video_url", "course__id", "course__title", "module__title"))
    return [{
        "id": l.id, "title": l.title, "description": l.description or "", "course_id": l.course_id,
        "course_title": l.course.title, "module_title": l.module.title if l.module else "",
        "duration_seconds": l.duration, "video_url": to_embed_url(decrypt_video_url(l.video_url)),
    } for l in qs if l.video_url]
