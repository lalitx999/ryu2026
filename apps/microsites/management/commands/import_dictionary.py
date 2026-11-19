from django.core.management.base import BaseCommand

from microsites.services.dict_import import export_thai_drafts, import_thai_drafts, import_words


class Command(BaseCommand):
    help = ("Load / refresh the JMdict common-words dictionary (22k words) and fill bundled Thai AI drafts for words "
            "without Thai.  --export-thai writes the current Thai entries to the bundle.")

    def add_arguments(self, parser):
        parser.add_argument("--export-thai", action="store_true")

    def handle(self, *args, **opts):
        if opts["export_thai"]:
            self.stdout.write(self.style.SUCCESS(f"exported {export_thai_drafts()} Thai entries"))
            return
        created, updated = import_words()
        drafts = import_thai_drafts()
        self.stdout.write(self.style.SUCCESS(f"words: {created} created, {updated} refreshed, {drafts} Thai drafts filled"))
