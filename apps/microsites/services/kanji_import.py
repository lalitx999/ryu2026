"""Load the bundled open kanji data into the Kanji table.  Re-runnable: open-data fields are refreshed,
Thai fields written by AI / teachers are left alone."""
import gzip
import json
from pathlib import Path

from django.db import transaction

from microsites.models import Kanji

SEED = Path(__file__).resolve().parent.parent / "data" / "kanji_seed.json.gz"
THAI_DRAFTS = Path(__file__).resolve().parent.parent / "data" / "kanji_th_drafts.json.gz"
THAI_FIELDS = ["th_meaning", "th_note", "examples", "ai_status", "ai_model"]
OPEN_FIELDS = ["level", "sort", "stroke_count", "frequency", "grade", "on_readings", "kun_readings", "meanings_en", "stroke_paths"]


def load_seed(path=SEED):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


@transaction.atomic
def import_kanji(rows=None):
    rows = rows if rows is not None else load_seed()
    existing = {k.char: k for k in Kanji.objects.all()}
    create, update = [], []
    for i, r in enumerate(rows):
        values = {"level": r["lv"], "sort": i, "stroke_count": r.get("sc") or len(r.get("sp") or []), "frequency": r.get("fr"),
                  "grade": r.get("gr"), "on_readings": r.get("on") or [], "kun_readings": r.get("kun") or [],
                  "meanings_en": r.get("en") or [], "stroke_paths": r.get("sp") or []}
        obj = existing.get(r["c"])
        if obj is None:
            create.append(Kanji(char=r["c"], **values))
        else:
            for k, v in values.items():
                setattr(obj, k, v)
            update.append(obj)
    Kanji.objects.bulk_create(create, batch_size=500)
    if update:
        Kanji.objects.bulk_update(update, OPEN_FIELDS, batch_size=500)
    return len(create), len(update)


def export_thai_drafts(path=THAI_DRAFTS):
    """Write every AI draft / approved Thai entry to a bundled file, so a fresh server gets them without calling AI."""
    rows = list(Kanji.objects.exclude(ai_status=Kanji.AI_NONE).order_by("sort")
                .values("char", "th_meaning", "th_note", "examples", "ai_model"))
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, separators=(",", ":"))
    return len(rows)


@transaction.atomic
def import_thai_drafts(path=THAI_DRAFTS):
    """Fill Thai fields from the bundled drafts, only for kanji that have no Thai yet (never touches reviewed rows)."""
    if not Path(path).exists():
        return 0
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        drafts = {d["char"]: d for d in json.load(fh)}
    todo = list(Kanji.objects.filter(ai_status=Kanji.AI_NONE, char__in=list(drafts)))
    for k in todo:
        d = drafts[k.char]
        k.th_meaning, k.th_note, k.examples = d["th_meaning"], d.get("th_note", ""), d.get("examples") or []
        k.ai_status, k.ai_model = Kanji.AI_DRAFT, d.get("ai_model", "")
    Kanji.objects.bulk_update(todo, THAI_FIELDS, batch_size=500)
    return len(todo)
