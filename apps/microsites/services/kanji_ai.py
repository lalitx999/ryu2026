"""AI drafts of the Thai fields for RYU KANJI (DeepSeek -> Groq via support.ai).  Sync HTTP: call from Celery or a
management command only.  Drafts are shown with an "AI draft" label until a teacher approves them."""
import json
import logging
import re

from microsites.models import Kanji
from support import ai

logger = logging.getLogger(__name__)
KANA_ONLY = re.compile(r"^[぀-ヿー]+$")

SYSTEM = (
    "คุณคือครูสอนภาษาญี่ปุ่นชาวไทยที่แม่นยำ เขียนสื่อการสอนคันจิสำหรับผู้เรียนคนไทย "
    "ตอบเป็น JSON array เท่านั้น ห้ามมีข้อความอื่น"
)


def _prompt(batch):
    lines = []
    for k in batch:
        lines.append(f'{k.char} | ระดับ {k.level} | on: {"、".join(k.on_readings) or "-"} | kun: {"、".join(k.kun_readings) or "-"} | en: {"; ".join(k.meanings_en)}')
    return (
        "สำหรับคันจิแต่ละตัวด้านล่าง ให้เขียน:\n"
        '- "th_meaning": ความหมายภาษาไทย สั้นกระชับ 1–4 คำ คั่นด้วยจุลภาค\n'
        '- "th_note": เทคนิคช่วยจำหรือข้อสังเกตการใช้ 1 ประโยคภาษาไทย ไม่เกิน 120 ตัวอักษร\n'
        '- "examples": คำศัพท์ที่ใช้คันจิตัวนั้นจริง 3 คำ ใช้บ่อยและไม่ยากเกินระดับที่ระบุ '
        'แต่ละคำเป็น {"word": คำศัพท์ภาษาญี่ปุ่น, "reading": คำอ่านเป็นฮิรางานะ, "th": ความหมายไทย}\n'
        'ตอบในรูป [{"char": "...", "th_meaning": "...", "th_note": "...", "examples": [...]}] ตามลำดับเดิม\n\n'
        + "\n".join(lines)
    )


def _parse(text):
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def _clean_examples(char, items):
    out = []
    for e in items or []:
        if not isinstance(e, dict):
            continue
        word, reading, th = str(e.get("word", "")).strip(), str(e.get("reading", "")).strip(), str(e.get("th", "")).strip()
        if char in word and KANA_ONLY.match(reading or "-") and th:   # keep only words that really use this kanji
            out.append({"word": word[:20], "reading": reading[:30], "th": th[:80]})
    return out[:3]


def draft(batch):
    """Ask the AI for one batch (a few kanji) and save the drafts.  Returns how many rows were updated."""
    batch = [k for k in batch if k.ai_status != Kanji.AI_APPROVED]
    if not batch:
        return 0
    result = ai.complete([{"role": "system", "content": SYSTEM}, {"role": "user", "content": _prompt(batch)}],
                         max_tokens=2600, temperature=0.3, timeout=90)
    if result is None:
        logger.warning("kanji AI draft: no provider answered")
        return 0
    by_char = {str(d.get("char", "")).strip(): d for d in _parse(result.text) if isinstance(d, dict)}
    saved = 0
    for k in batch:
        d = by_char.get(k.char)
        if not d or not str(d.get("th_meaning", "")).strip():
            continue
        k.th_meaning = str(d["th_meaning"]).strip()[:255]
        k.th_note = str(d.get("th_note", "")).strip()[:400]
        k.examples = _clean_examples(k.char, d.get("examples"))
        k.ai_status, k.ai_model = Kanji.AI_DRAFT, result.model[:80]
        k.save(update_fields=["th_meaning", "th_note", "examples", "ai_status", "ai_model", "updated_at"])
        saved += 1
    return saved


def pending(level=None, limit=40):
    qs = Kanji.objects.filter(ai_status=Kanji.AI_NONE)
    if level:
        qs = qs.filter(level=level)
    return list(qs.order_by("sort")[:limit])


def draft_pending(level=None, limit=40, batch_size=8, on_batch=None):
    todo, saved = pending(level, limit), 0
    for i in range(0, len(todo), batch_size):
        n = draft(todo[i:i + batch_size])
        saved += n
        if on_batch:
            on_batch(i + batch_size, len(todo), n)
    return saved
