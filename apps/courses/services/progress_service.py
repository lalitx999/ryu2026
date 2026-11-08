from django.db import transaction
from django.utils import timezone

from core.http import ServiceError
from courses.models import Lesson, Note, Progress, StudyActivityLog


@transaction.atomic
def save_progress(user, lesson_id, video_time=0, is_completed=False, set_completed=None):
    """`set_completed` (True/False) lets the player's toggle button un-mark a lesson; None keeps the old behaviour."""
    lesson = Lesson.objects.filter(id=lesson_id).only("id").first()
    if not lesson:
        raise ServiceError("ไม่พบบทเรียน", status=404)
    try:
        seconds = int(float(video_time or 0))
    except (TypeError, ValueError):
        seconds = 0
    progress, created = Progress.objects.get_or_create(
        user=user, lesson=lesson,
        defaults={"video_time": seconds, "is_completed": bool(is_completed) if set_completed is None else bool(set_completed)})
    if not created:
        progress.video_time = seconds
        if is_completed:
            progress.is_completed = True
        if set_completed is not None:
            progress.is_completed = bool(set_completed)
        progress.save()

    # Daily study log feeds the streak calendar on the profile window.
    today = timezone.localdate()
    log, _ = StudyActivityLog.objects.get_or_create(user=user, date=today)
    minutes = max(1, seconds // 60) if seconds else 5
    log.minutes_spent = max(log.minutes_spent, minutes)
    if is_completed:
        log.lessons_completed = (
            Progress.objects.filter(user=user, is_completed=True, completed_at__date=today).count()
            or log.lessons_completed + 1)
    log.save()
    return progress


def get_note(user, lesson_id):
    return Note.objects.filter(user=user, lesson_id=lesson_id).first()


def save_note(user, lesson_id, content):
    if not Lesson.objects.filter(id=lesson_id).exists():
        raise ServiceError("ไม่พบบทเรียน", status=404)
    note, _ = Note.objects.update_or_create(user=user, lesson_id=lesson_id, defaults={"content": content or ""})
    return note
