from payments.models import Payment
from courses.models import Enrollment
from courses.services.access_service import AccessService


def profile_payload(user):
    """Everything the desktop needs to know about the signed-in student, in 3 queries."""
    enrollments = list(
        Enrollment.objects.filter(user=user, is_active=True)
        .select_related("course")
        .only("course_id", "is_lifetime_video", "video_expires_at", "zoom_expires_at", "course__title", "course__level")
    )
    rank = AccessService.LEVEL_RANK
    best = max(enrollments, key=lambda e: rank.get(e.course.level, 0), default=None)
    is_lifetime = any(e.is_lifetime_video for e in enrollments)
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "nickname": user.nickname,
        "phone": user.phone,
        "role": user.role,
        "total_spent": float(user.total_spent or 0),
        "is_affiliate": user.is_affiliate,
        "is_lifetime": is_lifetime,
        "level": best.course.level if best else "N5",
        "has_pending_payment": Payment.objects.filter(user=user, status="pending").exists(),
        "courses_access": [
            {
                "course_id": e.course_id,
                "course_title": e.course.title,
                "is_lifetime": e.is_lifetime_video,
                "video_expires_at": e.video_expires_at.isoformat() if e.video_expires_at else None,
                "zoom_expires_at": e.zoom_expires_at.isoformat() if e.zoom_expires_at else None,
            }
            for e in enrollments
        ],
        "lifetime_progress": AccessService.get_tier_progress(user.total_spent),
    }
