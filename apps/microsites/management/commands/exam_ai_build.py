from django.core.management.base import BaseCommand

from microsites.services import exam_ai

PLAN = {"vocab": (3, 8), "kanji": (3, 8), "grammar": (3, 8), "reading": (4, 2), "listening": (2, 5)}   # rounds x per round


class Command(BaseCommand):
    help = "Build the mock-JLPT question bank with AI (generate + independent AI check)"

    def add_arguments(self, parser):
        parser.add_argument("--levels", nargs="+", default=["N5", "N4", "N3", "N2", "N1"])
        parser.add_argument("--sections", nargs="+", default=list(PLAN))
        parser.add_argument("--rounds", type=int, help="override the number of rounds per section")

    def handle(self, *args, **o):
        total = 0
        for level in o["levels"]:
            for section in o["sections"]:
                rounds, n = PLAN[section]
                for _ in range(o["rounds"] or rounds):
                    made, kept = exam_ai.build(level, section, n)
                    total += kept
                    self.stdout.write(f"{level} {section}: {kept}/{made} kept")
                    self.stdout.flush()
        self.stdout.write(self.style.SUCCESS(f"saved {total} questions"))
