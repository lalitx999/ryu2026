"""Read side of RYU DICTIONARY: search by Japanese (kanji / kana), Thai or English, and the word page."""
import re

from django.db.models import Q

from microsites import dict_labels, kana
from microsites.models import DictEntry, DictThaiQuery

THAI = re.compile(r"[฀-๿]")
JAPANESE = re.compile(r"[぀-ヿ一-鿿々ー]")
LIST_FIELDS = ("id", "jmdict_id", "headword", "reading", "senses", "th_gloss", "ai_status", "rank")


def script_of(q):
    if JAPANESE.search(q):
        return "ja"
    if THAI.search(q):
        return "th"
    return "en"


def _card(e):
    senses = e["senses"] or [{}]
    return {"id": e["id"], "word": e["headword"], "reading": e["reading"] if e["reading"] != e["headword"] else "",
            "th": e["th_gloss"], "en": "; ".join((senses[0].get("g") or [])[:3]), "pos": (senses[0].get("pos") or [""])[0],
            "ai": e["ai_status"]}


def search(query, limit=30):
    """Returns {"script", "results", "thai_cached"}.  Thai words without a cached AI answer get thai_cached=False so the
    page can offer "ask AI"."""
    q = (query or "").strip()[:64]
    if not q:
        return {"script": "", "results": [], "thai_cached": True}
    script = script_of(q)
    if script == "ja":
        variants = {q, kana.to_hiragana(q), kana.to_katakana(q)}
        exact = Q()
        prefix = Q()
        for v in variants:
            exact |= Q(keys__contains=f"|{v}|")
            prefix |= Q(keys__contains=f"|{v}")
        rows = list(DictEntry.objects.filter(exact).values(*LIST_FIELDS)[:limit])
        if len(rows) < limit:
            seen = {r["id"] for r in rows}
            rows += [r for r in DictEntry.objects.filter(prefix).exclude(id__in=seen).values(*LIST_FIELDS)[:limit - len(rows)]]
        return {"script": script, "results": [_card(r) for r in rows], "thai_cached": True}
    if script == "th":
        cached = DictThaiQuery.objects.filter(query=q).first()
        ids = cached.entry_ids if cached else []
        by_id = {r["id"]: r for r in DictEntry.objects.filter(id__in=ids).values(*LIST_FIELDS)}
        rows = [by_id[i] for i in ids if i in by_id]
        seen = {r["id"] for r in rows}
        rows += [r for r in DictEntry.objects.filter(th_gloss__icontains=q).exclude(id__in=seen).values(*LIST_FIELDS)[:limit - len(rows)]]
        return {"script": script, "results": [_card(r) for r in rows[:limit]], "thai_cached": bool(cached),
                "suggestions": cached.suggestions if cached else []}
    low = q.lower()
    rows = list(DictEntry.objects.filter(gloss_text__icontains=low).values(*LIST_FIELDS)[:200])
    # whole-word matches first ("eat" before "eating" / "theater")
    word = re.compile(rf"(^|[ ;(]){re.escape(low)}($|[ ;),])")
    rows.sort(key=lambda r: (not any(word.search(g.lower()) for s in r["senses"] for g in s.get("g", [])), r["rank"]))
    return {"script": script, "results": [_card(r) for r in rows[:limit]], "thai_cached": True}


def word(entry_id, tags):
    e = DictEntry.objects.filter(pk=entry_id).first()
    if e is None:
        return None
    senses = [{"pos": [dict_labels.pos_label(p, tags) for p in s.get("pos", [])], "g": s.get("g", [])} for s in e.senses]
    kanji = []
    for c in dict.fromkeys(e.headword):
        if "一" <= c <= "鿿":
            kanji.append(c)
    return {"e": e, "senses": senses, "th_reading": kana.reading_to_thai(e.reading), "kanji_chars": kanji,
            "other_forms": [f for f in e.forms if f != e.headword] + [r for r in e.readings if r != e.reading]}


def basics(limit=24):
    return [_card(r) for r in DictEntry.objects.exclude(ai_status=DictEntry.AI_NONE).order_by("rank").values(*LIST_FIELDS)[:limit]]
