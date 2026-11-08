from celery import shared_task

from courses.services import reminder_service


@shared_task
def send_renewal_reminders(days=None, include_expired=False):
    """Daily job (Celery beat): remind students whose access ends in 3/2/1 days."""
    sent = failed = 0
    for e in reminder_service.due_enrollments(days or reminder_service.DEFAULT_DAYS, include_expired).iterator(chunk_size=200):
        if reminder_service.send_reminder(e):
            sent += 1
        else:
            failed += 1
    return {"sent": sent, "failed": failed}


@shared_task
def send_reminders_for(enrollment_ids):
    from courses.models import Enrollment
    sent = failed = 0
    for e in Enrollment.objects.filter(pk__in=enrollment_ids, is_lifetime_video=False).select_related("user", "course"):
        if reminder_service.send_reminder(e, dedupe=False):
            sent += 1
        else:
            failed += 1
    return {"sent": sent, "failed": failed}
