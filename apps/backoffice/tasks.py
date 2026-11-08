from celery import shared_task

from backoffice.services import user_admin_service


@shared_task
def import_students(rows):
    """Bulk student import: password hashing makes this too slow for a web request."""
    return user_admin_service.import_students(rows)
