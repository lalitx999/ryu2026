from django.core.management.base import BaseCommand

from microsites.services import dict_ai


class Command(BaseCommand):
    help = "Write Thai meanings / explanations / example sentences with AI for the most basic dictionary words"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=3000)
        parser.add_argument("--batch", type=int, default=10)

    def handle(self, *args, **o):
        def progress(done, total, n):
            self.stdout.write(f"  {done}/{total} (+{n})", ending="\n")
            self.stdout.flush()
        saved = dict_ai.draft_pending(o["limit"], o["batch"], progress)
        self.stdout.write(self.style.SUCCESS(f"explained {saved} words"))
