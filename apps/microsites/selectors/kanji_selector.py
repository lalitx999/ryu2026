"""Read side of RYU KANJI.  The whole list is small (2,211 rows), so search runs in Python over a cached index."""
from django.core.cache import cache
from django.db.models import Count, Max

from microsites import kana
from microsites.models import Kanji

LEVELS = ["N5", "N4", "N3", "N2", "N1"]
LIST_FIELDS = ("char", "level", "stroke_count", "meanings_en", "th_meaning", "ai_status")


def level_counts():
    rows = Kanji.objects.values("level").annotate(n=Count("id"))
    found = {r["level"]: r["n"] for r in rows}
    return [(lv, found.get(lv, 0)) for lv in LEVELS]


def all_chars():
    return list(Kanji.objects.values_list("char", flat=True))


def level_list(level):
    """Grid of one level, in frequency order (one query)."""
    return list(Kanji.objects.filter(level=level).values(*LIST_FIELDS))


def detail(char):
    k = Kanji.objects.filter(char=char).first()
    if k is None:
        return None
    siblings = Kanji.objects.filter(level=k.level)
    prev = siblings.filter(sort__lt=k.sort).order_by("-sort").values_list("char", flat=True).first()
    nxt = siblings.filter(sort__gt=k.sort).order_by("sort").values_list("char", flat=True).first()
    return {
        "k": k,
        "on": [{"kana": kana.to_katakana_reading(r), "thai": kana.reading_to_thai(r)} for r in k.on_readings],
        "kun": [{"kana": r.replace("-", ""), "thai": kana.reading_to_thai(r)} for r in k.kun_readings],
        "prev": prev, "next": nxt,
        "position": siblings.filter(sort__lt=k.sort).count() + 1, "level_total": siblings.count(),
    }


def _index():
    stamp = Kanji.objects.aggregate(m=Max("updated_at"), n=Count("id"))
    key = f"ryu_kanji_index:{stamp['n']}:{stamp['m'].timestamp() if stamp['m'] else 0}"
    rows = cache.get(key)
    if rows is None:
        rows = []
        for r in Kanji.objects.values("char", "level", "on_readings", "kun_readings", "meanings_en", "th_meaning"):
            readings = [kana.to_hiragana(x).replace(".", "").replace("-", "") for x in r["on_readings"] + r["kun_readings"]]
            rows.append({"char": r["char"], "level": r["level"], "th": r["th_meaning"], "en": ", ".join(r["meanings_en"][:3]),
                         "readings": readings, "hay": (" ".join(r["meanings_en"]) + " " + r["th_meaning"]).lower()})
        cache.set(key, rows, 600)
    return rows


def search(query, limit=40):
    """Kanji characters, kana readings (hiragana or katakana), or Thai / English meaning words."""
    q = (query or "").strip()
    if not q:
        return []
    rows = _index()
    chars = [c for c in q if "一" <= c <= "鿿"]
    if chars:
        order = {c: i for i, c in enumerate(chars)}
        hits = sorted((r for r in rows if r["char"] in order), key=lambda r: order[r["char"]])
    elif all("぀" <= c <= "ヿ" for c in q):
        h = kana.to_hiragana(q)
        exact = [r for r in rows if h in r["readings"]]
        starts = [r for r in rows if r not in exact and any(x.startswith(h) for x in r["readings"])]
        hits = exact + starts
    else:
        low = q.lower()
        hits = [r for r in rows if low in r["hay"]]
    return [{k: r[k] for k in ("char", "level", "th", "en")} for r in hits[:limit]]
