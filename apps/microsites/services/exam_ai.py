"""AI-written mock JLPT questions for วัดระดับภาษาญี่ปุ่น.online.

Two passes (sync HTTP, run from a management command or Celery only):
1. `generate` asks the AI for new questions in the JLPT *format* for one level + section (original content, never real
   test items) and validates the shape;
2. `verify` gives the same questions to the AI again without the key; only questions it answers the same way are kept.
"""
import json
import logging
import random
import uuid

from microsites.models import ExamItem
from support import ai

logger = logging.getLogger(__name__)
SYSTEM = ("คุณคือผู้เชี่ยวชาญการออกข้อสอบภาษาญี่ปุ่นแนว JLPT แต่งโจทย์ใหม่ทั้งหมด ห้ามคัดลอกข้อสอบจริง "
          "ระดับความยากต้องตรงกับระดับที่กำหนด คำอธิบายเฉลยเขียนเป็นภาษาไทย โดยอ้างถึงตัวคำตอบ ห้ามอ้างเลขข้อหรือลำดับตัวเลือก "
          "ตอบเป็น JSON เท่านั้น ห้ามมีข้อความอื่น")

PASSAGE_LEN = {"N5": "80–120", "N4": "120–180", "N3": "200–300", "N2": "300–400", "N1": "400–550"}

FORMATS = {
    "vocab": ('โจทย์เติมคำศัพท์: ประโยคภาษาญี่ปุ่นที่มีช่องว่าง （　　） 1 ช่อง ให้เลือกคำศัพท์ที่เหมาะสมที่สุด '
              'ตัวเลือก 4 คำเป็นคำประเภทเดียวกัน มีคำตอบถูกเพียงข้อเดียว'),
    "kanji": ('โจทย์คำอ่านคันจิ: ประโยคภาษาญี่ปุ่นที่มีคำหนึ่งคำครอบด้วย 【】 (เช่น 【学校】) ให้เลือกคำอ่านที่ถูกต้อง '
              'ตัวเลือก 4 ข้อเป็นฮิรางานะที่หน้าตาคล้ายกัน (เช่น ต่างที่เสียงสั้นยาว เสียงขุ่น หรือっ) มีคำตอบถูกเพียงข้อเดียว'),
    "grammar": ('โจทย์ไวยากรณ์: ประโยคภาษาญี่ปุ่นที่มีช่องว่าง （　　） ให้เลือกรูปไวยากรณ์ คำช่วย หรือการผันที่ถูกต้อง '
                'ใช้รูปไวยากรณ์ของระดับนี้ มีคำตอบถูกเพียงข้อเดียว'),
}


def _json(text):
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def _valid(q):
    choices = [str(c).strip() for c in (q.get("choices") or [])]
    try:
        answer = int(q.get("answer"))
    except (TypeError, ValueError):
        return None
    if len(choices) != 4 or len(set(choices)) != 4 or not all(choices) or not 0 <= answer <= 3 or not str(q.get("stem", "")).strip():
        return None
    # AI writers put the right answer first far too often: shuffle so the key's position carries no hint
    right = choices[answer]
    random.shuffle(choices)
    return {"stem": str(q["stem"]).strip()[:600], "choices": [c[:120] for c in choices], "answer": choices.index(right),
            "explanation": str(q.get("explanation", "")).strip()[:600]}


def _prompt(level, section, n):
    if section in FORMATS:
        return (f"ระดับ JLPT {level} · {FORMATS[section]}\nแต่งโจทย์ {n} ข้อ ไม่ซ้ำกัน หัวข้อหลากหลาย\n"
                'ตอบในรูป [{"stem": "ประโยคโจทย์", "choices": ["ก", "ข", "ค", "ง"], "answer": ดัชนีคำตอบที่ถูก 0-3, '
                '"explanation": "อธิบายเฉลยภาษาไทย 1–2 ประโยค"}]')
    if section == "reading":
        return (f"ระดับ JLPT {level} · การอ่านจับใจความ: แต่งบทอ่านภาษาญี่ปุ่นใหม่ {n} บท แต่ละบทยาวประมาณ {PASSAGE_LEN[level]} ตัวอักษร "
                "(เช่น จดหมาย ประกาศ บันทึก บทความสั้น) แต่ละบทมีคำถามภาษาญี่ปุ่น 2 ข้อ ข้อละ 4 ตัวเลือก มีคำตอบถูกข้อเดียว\n"
                'ตอบในรูป [{"passage": "บทอ่าน", "questions": [{"stem": "คำถาม", "choices": [...4], "answer": 0-3, '
                '"explanation": "อธิบายเฉลยภาษาไทย"}]}]')
    return (f"ระดับ JLPT {level} · การฟัง: แต่งบทสนทนาภาษาญี่ปุ่นสั้น ๆ ใหม่ {n} บท ระหว่าง 2 คน เขียนเป็นบรรทัด ขึ้นต้นด้วย「男：」หรือ「女：」 "
            "ยาว 3–8 บรรทัดตามระดับ แต่ละบทมีคำถามภาษาญี่ปุ่น 1 ข้อ (ถามสิ่งที่ฟังจากบทสนทนา) ตัวเลือก 4 ข้อเป็นข้อความสั้น มีคำตอบถูกข้อเดียว\n"
            'ตอบในรูป [{"script": "บทสนทนา", "stem": "คำถาม", "choices": [...4], "answer": 0-3, "explanation": "อธิบายเฉลยภาษาไทย"}]')


def generate(level, section, n):
    """Return unsaved ExamItem objects (already shape-checked, not yet verified)."""
    result = ai.complete([{"role": "system", "content": SYSTEM}, {"role": "user", "content": _prompt(level, section, n)}],
                         max_tokens=3800, temperature=0.8, timeout=120)
    if result is None:
        return []
    items = []
    for raw in _json(result.text):
        if not isinstance(raw, dict):
            continue
        if section == "reading":
            passage = str(raw.get("passage", "")).strip()[:2000]
            group = "r-" + uuid.uuid4().hex[:10]
            for q in (raw.get("questions") or [])[:3]:
                v = _valid(q) if isinstance(q, dict) else None
                if v and passage:
                    items.append(ExamItem(level=level, section=section, group=group, passage=passage, ai_model=result.model[:80], **v))
        else:
            v = _valid(raw)
            if not v:
                continue
            passage = str(raw.get("script", "")).strip()[:2000] if section == "listening" else ""
            if section == "listening" and not passage:
                continue
            if section == "kanji" and "【" not in v["stem"]:
                continue
            items.append(ExamItem(level=level, section=section, passage=passage, ai_model=result.model[:80],
                                  group=("l-" + uuid.uuid4().hex[:10]) if section == "listening" else "", **v))
    return items


def verify(items):
    """Solve the questions again without the key; keep only those answered the same way."""
    if not items:
        return []
    lines = []
    for i, q in enumerate(items):
        ctx = f"[บท] {q.passage}\n" if q.passage else ""
        lines.append(f"ข้อ {i}: {ctx}{q.stem}\n" + "\n".join(f"  {j}) {c}" for j, c in enumerate(q.choices)))
    result = ai.complete([{"role": "system", "content": "คุณคือผู้สอบภาษาญี่ปุ่นระดับเจ้าของภาษา ตอบเป็น JSON เท่านั้น"},
                          {"role": "user", "content": "ทำข้อสอบต่อไปนี้ ตอบในรูป [{\"q\": เลขข้อ, \"answer\": ดัชนีตัวเลือก 0-3}]\n\n" + "\n\n".join(lines)}],
                         max_tokens=800, temperature=0, timeout=120)
    if result is None:
        return []
    picked = {}
    for a in _json(result.text):
        if isinstance(a, dict):
            try:
                picked[int(a.get("q"))] = int(a.get("answer"))
            except (TypeError, ValueError):
                continue
    return [q for i, q in enumerate(items) if picked.get(i) == q.answer]


def build(level, section, n):
    """Generate, verify and save.  Returns (generated, saved)."""
    items = generate(level, section, n)
    kept = verify(items)
    if section in ("reading", "listening"):          # keep passages whole: drop a group if any of its questions failed
        kept_ids = {id(q) for q in kept}
        bad_groups = {q.group for q in items if id(q) not in kept_ids}
        kept = [q for q in kept if q.group not in bad_groups]
    ExamItem.objects.bulk_create(kept)
    return len(items), len(kept)
