"""AI help for RYU DICTIONARY (DeepSeek -> Groq via support.ai).  Sync HTTP: call from Celery / commands only.
JMdict stays the source of truth: AI writes the Thai explanation of a dictionary word, and for Thai queries AI only
proposes Japanese words that are then looked up in JMdict."""
import json
import logging
import re

from microsites import dict_labels
from microsites.models import DictEntry, DictThaiQuery
from support import ai

logger = logging.getLogger(__name__)
KANA_SENTENCE = re.compile(r"^[぀-ヿー\s、。！？「」・…]+$")
SYSTEM = "คุณคือครูสอนภาษาญี่ปุ่นชาวไทยที่แม่นยำ อธิบายคำศัพท์ให้ผู้เรียนคนไทย ตอบเป็น JSON เท่านั้น ห้ามมีข้อความอื่น"


def _json(text, kind="["):
    end_char = "]" if kind == "[" else "}"
    start, end = text.find(kind), text.rfind(end_char)
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except ValueError:
        return None


def _line(e):
    tags = dict_labels.jmdict_tags()
    senses = " / ".join(f'[{", ".join(dict_labels.pos_label(p, tags) for p in s.get("pos", []))}] ' + "; ".join(s.get("g", []))
                        for s in e.senses[:4])
    return f'{e.id} | {e.headword} | {e.reading} | {senses}'


def _prompt(batch):
    return (
        "สำหรับคำศัพท์แต่ละคำด้านล่าง (รูปแบบ: id | คำ | คำอ่าน | [ประเภทคำ] ความหมายภาษาอังกฤษจาก JMdict) ให้เขียน:\n"
        '- "th_gloss": ความหมายภาษาไทยตามความหมายอังกฤษที่ให้มา สั้นกระชับ คั่นแต่ละความหมายด้วย "; " ไม่เกิน 4 ความหมาย\n'
        '- "th_explain": อธิบายการใช้หรือความแตกต่างที่ควรรู้ 1–2 ประโยคภาษาไทย ไม่เกิน 200 ตัวอักษร '
        "ประเภทคำและกลุ่มกริยาให้ใช้ตามที่ระบุในวงเล็บเท่านั้น ห้ามเดาเอง (ถ้าไม่จำเป็นไม่ต้องกล่าวถึง)\n"
        '- "examples": ตัวอย่างประโยคง่าย ๆ ที่ใช้คำนี้จริง 2 ประโยค แต่ละประโยคเป็น {"ja": ประโยคภาษาญี่ปุ่น, '
        '"reading": คำอ่านทั้งประโยคเป็นฮิรางานะ, "th": คำแปลภาษาไทย}\n'
        'ตอบในรูป [{"id": ..., "th_gloss": "...", "th_explain": "...", "examples": [...]}]\n\n'
        + "\n".join(_line(e) for e in batch)
    )


def _clean_examples(e, items):
    forms = set(e.forms) | set(e.readings)
    out = []
    for x in items or []:
        if not isinstance(x, dict):
            continue
        ja, reading, th = (str(x.get(k, "")).strip() for k in ("ja", "reading", "th"))
        if ja and th and KANA_SENTENCE.match(reading or "-") and any(f[:2] in ja for f in forms if f):
            out.append({"ja": ja[:120], "reading": reading[:200], "th": th[:200]})
    return out[:3]


def explain(batch):
    """Write Thai for a few entries.  Returns how many were saved."""
    batch = [e for e in batch if e.ai_status == DictEntry.AI_NONE]
    if not batch:
        return 0
    result = ai.complete([{"role": "system", "content": SYSTEM}, {"role": "user", "content": _prompt(batch)}],
                         max_tokens=3000, temperature=0.3, timeout=90)
    data = _json(result.text) if result else None
    if not isinstance(data, list):
        logger.warning("dictionary AI: no usable answer")
        return 0
    by_id = {str(d.get("id")): d for d in data if isinstance(d, dict)}
    saved = 0
    for e in batch:
        d = by_id.get(str(e.id))
        if not d or not str(d.get("th_gloss", "")).strip():
            continue
        e.th_gloss = str(d["th_gloss"]).strip()[:255]
        e.th_explain = str(d.get("th_explain", "")).strip()[:500]
        e.examples = _clean_examples(e, d.get("examples"))
        e.ai_status, e.ai_model = DictEntry.AI_DRAFT, result.model[:80]
        e.save(update_fields=["th_gloss", "th_explain", "examples", "ai_status", "ai_model", "updated_at"])
        saved += 1
    return saved


def explain_one(entry_id):
    e = DictEntry.objects.filter(pk=entry_id).first()
    return explain([e]) if e else 0


def draft_pending(limit=3000, batch_size=10, on_batch=None):
    todo = list(DictEntry.objects.filter(ai_status=DictEntry.AI_NONE).order_by("rank")[:limit])
    saved = 0
    for i in range(0, len(todo), batch_size):
        n = explain(todo[i:i + batch_size])
        saved += n
        if on_batch:
            on_batch(min(i + batch_size, len(todo)), len(todo), n)
    return saved


def thai_lookup(query):
    """Ask AI which Japanese words mean a Thai word, keep the ones found in JMdict, cache the answer."""
    query = query.strip()[:100]
    cached = DictThaiQuery.objects.filter(query=query).first()
    if cached:
        return cached
    result = ai.complete([{"role": "system", "content": SYSTEM}, {"role": "user", "content": (
        f'คำภาษาไทย: "{query}"\nให้คำภาษาญี่ปุ่นที่มีความหมายตรงกัน 1–6 คำ เรียงจากใช้บ่อยที่สุด '
        'ตอบในรูป [{"word": "คำภาษาญี่ปุ่น (คันจิถ้ามี)", "reading": "คำอ่านฮิรางานะ"}]')}],
        max_tokens=500, temperature=0.2, timeout=40)
    data = _json(result.text) if result else None
    if not isinstance(data, list):
        return None      # do not cache failures
    ids, missing = [], []
    for item in data[:6]:
        if not isinstance(item, dict):
            continue
        w, r = str(item.get("word", "")).strip()[:30], str(item.get("reading", "")).strip()[:30]
        if not w:
            continue
        hit = DictEntry.objects.filter(keys__contains=f"|{w}|").order_by("rank").values_list("id", flat=True).first()
        if hit is None and r:
            hit = DictEntry.objects.filter(keys__contains=f"|{r}|", headword=w).values_list("id", flat=True).first()
        if hit is not None and hit not in ids:
            ids.append(hit)
        elif hit is None:
            missing.append({"word": w, "reading": r})
    obj, _ = DictThaiQuery.objects.get_or_create(query=query, defaults={"entry_ids": ids, "suggestions": missing})
    return obj
