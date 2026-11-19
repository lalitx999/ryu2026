"""Builds the mock tests for วัดระดับภาษาญี่ปุ่น.online from the published question bank."""
from django.db.models import Count
from django.utils.html import escape

from microsites.models import ExamItem

LEVELS = ["N5", "N4", "N3", "N2", "N1"]
MINUTES = {"N5": 40, "N4": 45, "N3": 60, "N2": 70, "N1": 80}          # shortened mock timing, not the official one
MOCK = {"vocab": 8, "kanji": 8, "grammar": 8}                          # single questions per section
MOCK_GROUPS = {"reading": 2, "listening": 3}                          # passages / dialogues per section
PLACEMENT_PER_LEVEL = 5
SECTION_TH = dict(ExamItem.SECTIONS)


def _published():
    return ExamItem.objects.exclude(status=ExamItem.HIDDEN)


def level_counts():
    rows = _published().values("level").annotate(n=Count("id"))
    found = {r["level"]: r["n"] for r in rows}
    return [{"level": lv, "count": found.get(lv, 0), "minutes": MINUTES[lv], "ready": found.get(lv, 0) >= 20} for lv in LEVELS]


def _stem_html(stem):
    return escape(stem).replace("【", "<u>").replace("】", "</u>")


def _payload(q):
    return {"id": q.id, "level": q.level, "section": q.section, "section_th": SECTION_TH[q.section], "group": q.group,
            "passage": q.passage, "stem": _stem_html(q.stem), "choices": q.choices, "answer": q.answer,
            "explanation": q.explanation, "approved": q.status == ExamItem.APPROVED}


def _singles(level, section, n):
    return list(_published().filter(level=level, section=section).order_by("?")[:n])


def _groups(level, section, n):
    groups = list(_published().filter(level=level, section=section).values_list("group", flat=True).distinct().order_by("?")[:n])
    return list(_published().filter(group__in=groups).order_by("group", "id"))


def mock(level):
    items = []
    for section, n in MOCK.items():
        items += _singles(level, section, n)
    for section, n in MOCK_GROUPS.items():
        items += _groups(level, section, n)
    return {"kind": "mock", "level": level, "minutes": MINUTES[level], "items": [_payload(q) for q in items]}


def placement():
    items = []
    for level in LEVELS:
        items += list(_published().filter(level=level, section__in=["vocab", "kanji", "grammar"]).order_by("?")[:PLACEMENT_PER_LEVEL])
    return {"kind": "placement", "level": "", "minutes": 20, "items": [_payload(q) for q in items]}
