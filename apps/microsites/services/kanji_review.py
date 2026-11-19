"""Teacher review of the Thai kanji content (admin panel)."""
import re

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone

from core.http import ServiceError
from microsites.models import Kanji

KANA_ONLY = re.compile(r"^[぀-ヿー]+$")


def review_page(level="", status="", q="", page=1):
    qs = Kanji.objects.all()
    if level:
        qs = qs.filter(level=level)
    counts = {r["ai_status"]: r["n"] for r in qs.values("ai_status").annotate(n=Count("id"))}
    if status:
        qs = qs.filter(ai_status=status)
    if q:
        qs = qs.filter(Q(char=q) | Q(th_meaning__icontains=q))
    return Paginator(qs.order_by("sort").only("id", "char", "level", "stroke_count", "on_readings", "kun_readings", "meanings_en",
                                              "th_meaning", "th_note", "examples", "ai_status", "ai_model", "reviewed_at"), 20).get_page(page), counts


def parse_examples(text):
    """One example per line: "word | reading | Thai meaning"."""
    out = []
    for line in (text or "").splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3 or not all(parts[:3]):
            if line.strip():
                raise ServiceError(f'รูปแบบคำศัพท์ไม่ถูกต้อง: "{line.strip()}" (ใช้ คำศัพท์ | คำอ่าน | ความหมาย)')
            continue
        if not KANA_ONLY.match(parts[1]):
            raise ServiceError(f'คำอ่านต้องเป็นฮิรางานะ/คาตากานะ: "{parts[1]}"')
        out.append({"word": parts[0][:20], "reading": parts[1][:30], "th": parts[2][:80]})
    return out[:6]


def save(pk, data, user):
    k = Kanji.objects.filter(pk=pk).first()
    if k is None:
        raise ServiceError("ไม่พบคันจินี้", status=404)
    meaning = str(data.get("th_meaning", "")).strip()
    approve = bool(data.get("approve"))
    if approve and not meaning:
        raise ServiceError("ใส่ความหมายภาษาไทยก่อนอนุมัติ")
    k.th_meaning = meaning[:255]
    k.th_note = str(data.get("th_note", "")).strip()[:400]
    k.examples = parse_examples(data.get("examples", ""))
    if approve:
        k.ai_status, k.reviewed_by, k.reviewed_at = Kanji.AI_APPROVED, user, timezone.now()
    else:   # "save as draft" also takes back an earlier approval
        k.ai_status = Kanji.AI_DRAFT if meaning else Kanji.AI_NONE
        k.reviewed_by, k.reviewed_at = None, None
    k.save()
    return k
