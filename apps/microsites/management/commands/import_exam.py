from django.core.management.base import BaseCommand

from microsites.services.exam_bank import export_bank, import_bank


class Command(BaseCommand):
    help = "Add the bundled mock-JLPT questions to the database (existing questions are kept).  --export writes the bundle."

    def add_arguments(self, parser):
        parser.add_argument("--export", action="store_true")

    def handle(self, *args, **opts):
        if opts["export"]:
            self.stdout.write(self.style.SUCCESS(f"exported {export_bank()} questions"))
        else:
            self.stdout.write(self.style.SUCCESS(f"added {import_bank()} questions"))
