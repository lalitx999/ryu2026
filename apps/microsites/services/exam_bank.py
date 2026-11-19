"""Bundle / restore the AI-written question bank (so a fresh server gets it without calling AI) and reader reports."""
import gzip
import json
from pathlib import Path

from django.core.cache import cache
from django.db import transaction
from django.db.models import F

from core.http import ServiceError
from microsites.models import ExamItem
from microsites.services.ratelimit import client_ip

BANK = Path(__file__).resolve().parent.parent / "data" / "exam_bank.json.gz"
FIELDS = ("level", "section", "group", "passage", "stem", "choices", "answer", "explanation", "ai_model")


def export_bank(path=BANK):
    rows = list(ExamItem.objects.exclude(status=ExamItem.HIDDEN).order_by("level", "section", "group", "id").values(*FIELDS))
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, separators=(",", ":"))
    return len(rows)


@transaction.atomic
def import_bank(path=BANK):
    """Add bundled questions whose stem (+ passage) is not in the table yet; never touches existing rows."""
    if not Path(path).exists():
        return 0
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        rows = json.load(fh)
    have = set(ExamItem.objects.values_list("stem", "passage"))
    new = [ExamItem(**r) for r in rows if (r["stem"], r["passage"]) not in have]
    ExamItem.objects.bulk_create(new, batch_size=500)
    return len(new)


def report(request, item_id):
    """A test taker flags a question as wrong (once per visitor per question)."""
    if not ExamItem.objects.filter(pk=item_id).exists():
        raise ServiceError("ไม่พบโจทย์นี้", status=404)
    if not cache.add(f"ryu_exam_report:{item_id}:{client_ip(request)}", 1, 86400 * 30):
        return False
    ExamItem.objects.filter(pk=item_id).update(reports=F("reports") + 1)
    return True

