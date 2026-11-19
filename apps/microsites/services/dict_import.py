"""Load the bundled JMdict (common words) into DictEntry.  Re-runnable; Thai fields are never overwritten."""
import gzip
import json
from pathlib import Path

from django.db import transaction

from microsites.models import DictEntry

DATA = Path(__file__).resolve().parent.parent / "data"
SEED = DATA / "jmdict_common.json.gz"
THAI_DRAFTS = DATA / "dict_th_drafts.json.gz"
OPEN_FIELDS = ["headword", "reading", "forms", "readings", "senses", "rank", "keys", "gloss_text"]
THAI_FIELDS = ["th_gloss", "th_explain", "examples", "ai_status", "ai_model"]


def load_seed(path=SEED):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def _values(w):
    forms, readings = w.get("k") or [], w.get("r") or []
    glosses = [g for s in w["s"] for g in s["g"]]
    return {"headword": (forms or readings)[0][:64], "reading": readings[0][:64], "forms": forms, "readings": readings,
            "senses": w["s"], "rank": w.get("rk", 0), "keys": "|" + "|".join(forms + readings) + "|",
            "gloss_text": " ; ".join(glosses).lower()}


@transaction.atomic
def import_words(words=None):
    words = words if words is not None else load_seed()["words"]
    existing = {e.jmdict_id: e for e in DictEntry.objects.only("id", "jmdict_id")}
    create, update = [], []
    for w in words:
        values = _values(w)
        obj = existing.get(w["id"])
        if obj is None:
            create.append(DictEntry(jmdict_id=w["id"], **values))
        else:
            for k, v in values.items():
                setattr(obj, k, v)
            update.append(obj)
    DictEntry.objects.bulk_create(create, batch_size=1000)
    if update:
        DictEntry.objects.bulk_update(update, OPEN_FIELDS, batch_size=1000)
    return len(create), len(update)


def export_thai_drafts(path=THAI_DRAFTS):
    rows = list(DictEntry.objects.exclude(ai_status=DictEntry.AI_NONE).order_by("rank")
                .values("jmdict_id", "th_gloss", "th_explain", "examples", "ai_model"))
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, separators=(",", ":"))
    return len(rows)


@transaction.atomic
def import_thai_drafts(path=THAI_DRAFTS):
    if not Path(path).exists():
        return 0
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        drafts = {d["jmdict_id"]: d for d in json.load(fh)}
    todo = list(DictEntry.objects.filter(ai_status=DictEntry.AI_NONE, jmdict_id__in=list(drafts)))
    for e in todo:
        d = drafts[e.jmdict_id]
        e.th_gloss, e.th_explain, e.examples = d["th_gloss"], d.get("th_explain", ""), d.get("examples") or []
        e.ai_status, e.ai_model = DictEntry.AI_DRAFT, d.get("ai_model", "")
    DictEntry.objects.bulk_update(todo, THAI_FIELDS, batch_size=1000)
    return len(todo)
