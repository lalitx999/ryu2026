"""RYU TRANSLATOR: Thai <-> Japanese with a chosen politeness level, notes on nuance and key words.
`request_translation` is called from the view (cache lookup only, never HTTP); `translate` calls the AI and runs in
Celery.  Results are cached by a hash of the input, so the same sentence is translated once."""
import hashlib
import json
import logging
import re
from datetime import timedelta

from django.utils import timezone

from core.http import ServiceError
from microsites import kana
from microsites.models import TranslationCache
from support import ai

logger = logging.getLogger(__name__)
MAX_CHARS = 500
STYLES = {"casual": "ภาษาทั่วไป/กันเอง (普通体)", "polite": "ภาษาสุภาพ (です・ます)", "business": "ภาษาธุรกิจ/ทางการ (敬語)"}
DIRECTIONS = ("th2ja", "ja2th")
THAI = re.compile(r"[฀-๿]")
JAPANESE = re.compile(r"[぀-ヿ一-鿿]")
KANA_TEXT = re.compile(r"^[぀-ヿー\s、。！？「」・…,.!?0-9０-９]+$")

SYSTEM = ("คุณคือล่ามแปลภาษาไทย–ญี่ปุ่นมืออาชีพ แปลให้เป็นธรรมชาติแบบที่เจ้าของภาษาพูดจริง ถูกต้องตามบริบท "
          "อธิบายให้ผู้เรียนคนไทยเข้าใจ ตอบเป็น JSON เท่านั้น ห้ามมีข้อความอื่น")


def clean_text(text):
    text = re.sub(r"[ \t]+", " ", str(text or "")).strip()
    if not text:
        raise ServiceError("พิมพ์ข้อความที่ต้องการแปลก่อนนะครับ")
    if len(text) > MAX_CHARS:
        raise ServiceError(f"ข้อความยาวเกิน {MAX_CHARS} ตัวอักษร ลองแบ่งเป็นช่วงสั้น ๆ นะครับ")
    return text


def detect(text):
    return "ja2th" if JAPANESE.search(text) and not THAI.search(text) else "th2ja"


def cache_key(text, direction, style):
    return hashlib.sha256(f"{direction}|{style}|{text}".encode("utf-8")).hexdigest()


def request_translation(text, direction="auto", style="polite"):
    """Validate and look up the cache.  Returns (key, direction, style, cached_result_or_None)."""
    text = clean_text(text)
    style = style if style in STYLES else "polite"
    direction = direction if direction in DIRECTIONS else detect(text)
    key = cache_key(text, direction, style)
    row = TranslationCache.objects.filter(key=key).first()
    if row:
        TranslationCache.objects.filter(pk=row.pk).update(hits=row.hits + 1)
        return key, direction, style, row.result
    return key, direction, style, None


def cached(key):
    row = TranslationCache.objects.filter(key=key).only("result").first()
    return row.result if row else None


def _prompt(text, direction, style):
    if direction == "th2ja":
        return (
            f"แปลข้อความภาษาไทยต่อไปนี้เป็นภาษาญี่ปุ่น ระดับภาษา: {STYLES[style]}\n"
            'ตอบในรูป {"translation": "คำแปลภาษาญี่ปุ่น", "reading": "คำอ่านของคำแปลทั้งหมดเป็นฮิรางานะ", '
            '"alternatives": [{"style": "casual|polite|business", "text": "คำแปลในระดับภาษาอื่น", "reading": "ฮิรางานะ"}], '
            '"notes": ["ข้อสังเกตภาษาไทยสั้น ๆ เรื่องสำนวน ความสุภาพ หรือความต่างของคำ ไม่เกิน 3 ข้อ"], '
            '"words": [{"word": "คำญี่ปุ่นสำคัญในประโยค", "reading": "ฮิรางานะ", "th": "ความหมายไทย"}]}\n'
            "alternatives ให้ใส่เฉพาะระดับภาษาอื่นอีก 2 ระดับ words ไม่เกิน 5 คำ\n\n"
            f"ข้อความ: {text}"
        )
    return (
        "แปลข้อความภาษาญี่ปุ่นต่อไปนี้เป็นภาษาไทยที่เป็นธรรมชาติ\n"
        'ตอบในรูป {"translation": "คำแปลภาษาไทย", "reading": "คำอ่านของต้นฉบับทั้งหมดเป็นฮิรางานะ", '
        '"politeness": "ต้นฉบับใช้ระดับภาษาแบบไหน อธิบายสั้น ๆ เป็นภาษาไทย", '
        '"notes": ["ข้อสังเกตภาษาไทยสั้น ๆ เรื่องสำนวนหรือไวยากรณ์ที่น่าสนใจ ไม่เกิน 3 ข้อ"], '
        '"words": [{"word": "คำญี่ปุ่นสำคัญในต้นฉบับ", "reading": "ฮิรางานะ", "th": "ความหมายไทย"}]}\n'
        "words ไม่เกิน 5 คำ\n\n"
        f"ข้อความ: {text}"
    )


def _parse(text):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _kana_or_blank(value):
    value = str(value or "").strip()[:600]
    return value if value and KANA_TEXT.match(value) else ""


def _clean(data, direction, style):
    reading = _kana_or_blank(data.get("reading"))
    # a Thai transliteration helps for short phrases; for long sentences it becomes unreadable, so skip it
    short = reading and len(reading.replace(" ", "")) <= 20
    out = {"direction": direction, "style": style, "translation": str(data.get("translation", "")).strip()[:1500],
           "reading": reading, "reading_th": kana.reading_to_thai(reading.replace(" ", "")) if short else "",
           "notes": [str(n).strip()[:240] for n in (data.get("notes") or []) if str(n).strip()][:3],
           "words": [], "alternatives": [], "politeness": str(data.get("politeness", "")).strip()[:240]}
    for w in (data.get("words") or [])[:5]:
        if isinstance(w, dict) and str(w.get("word", "")).strip():
            out["words"].append({"word": str(w["word"]).strip()[:30], "reading": _kana_or_blank(w.get("reading"))[:40],
                                 "th": str(w.get("th", "")).strip()[:80]})
    for a in (data.get("alternatives") or [])[:2]:
        if isinstance(a, dict) and a.get("style") in STYLES and a.get("style") != style and str(a.get("text", "")).strip():
            out["alternatives"].append({"style": a["style"], "label": STYLES[a["style"]], "text": str(a["text"]).strip()[:600],
                                        "reading": _kana_or_blank(a.get("reading"))})
    return out


def translate(text, direction, style, key):
    """Call the AI and store the result under `key`.  Returns the result dict, or None when no provider answered."""
    if cached(key):
        return cached(key)
    result = ai.complete([{"role": "system", "content": SYSTEM}, {"role": "user", "content": _prompt(text, direction, style)}],
                         max_tokens=1500, temperature=0.3, timeout=60)
    data = _parse(result.text) if result else None
    if not data or not str(data.get("translation", "")).strip():
        logger.warning("translator: no usable answer")
        return None
    clean = _clean(data, direction, style)
    clean["model"] = result.model
    TranslationCache.objects.get_or_create(key=key, defaults={"direction": direction, "style": style, "result": clean})
    return clean


def purge(days=30):
    return TranslationCache.objects.filter(created_at__lt=timezone.now() - timedelta(days=days)).delete()[0]
