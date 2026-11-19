from django.core.management.base import BaseCommand

from microsites.services import kanji_ai


class Command(BaseCommand):
    help = "Draft Thai meanings / notes / examples with AI for kanji that have none yet (shown as AI drafts)"

    def add_arguments(self, parser):
        parser.add_argument("--level", choices=["N5", "N4", "N3", "N2", "N1"])
        parser.add_argument("--limit", type=int, default=80)
        parser.add_argument("--batch", type=int, default=8)

    def handle(self, *args, **o):
        def progress(done, total, n):
            self.stdout.write(f"  {min(done, total)}/{total} (+{n})")
        saved = kanji_ai.draft_pending(o["level"], o["limit"], o["batch"], progress)
        self.stdout.write(self.style.SUCCESS(f"drafted {saved} kanji"))
