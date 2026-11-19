from django.core.management.base import BaseCommand

from microsites.services.kanji_import import export_thai_drafts, import_kanji, import_thai_drafts


class Command(BaseCommand):
    help = ("Load / refresh the 2,211 JLPT kanji from the bundled open data, then fill Thai AI drafts for kanji that "
            "have none (reviewed Thai is never overwritten).  --export-thai writes the current drafts to the bundle.")

    def add_arguments(self, parser):
        parser.add_argument("--export-thai", action="store_true")

    def handle(self, *args, **opts):
        if opts["export_thai"]:
            self.stdout.write(self.style.SUCCESS(f"exported {export_thai_drafts()} Thai entries"))
            return
        created, updated = import_kanji()
        drafts = import_thai_drafts()
        self.stdout.write(self.style.SUCCESS(f"kanji: {created} created, {updated} refreshed, {drafts} Thai drafts filled"))
