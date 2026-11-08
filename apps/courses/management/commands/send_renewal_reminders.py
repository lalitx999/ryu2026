from django.core.management.base import BaseCommand

from courses.services import reminder_service


class Command(BaseCommand):
    help = "Send renewal reminder emails to students whose access expires soon (or expired within 30 days)."

    def add_arguments(self, parser):
        parser.add_argument("--days", nargs="+", type=int, default=list(reminder_service.DEFAULT_DAYS))
        parser.add_argument("--include-expired", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **o):
        qs = reminder_service.due_enrollments(o["days"], o["include_expired"])
        sent = failed = 0
        for e in qs.iterator(chunk_size=200):
            self.stdout.write(f"{e.user.email} | {e.course.title} | expires {e.video_expires_at}")
            if o["dry_run"] or reminder_service.send_reminder(e):
                sent += 1
            else:
                failed += 1
        self.stdout.write(self.style.SUCCESS(f"{'(dry run) ' if o['dry_run'] else ''}{sent} sent/queued, {failed} failed"))
