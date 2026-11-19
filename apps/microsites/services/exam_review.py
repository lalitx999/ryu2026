"""Teacher review of the mock-JLPT question bank (admin panel)."""
from django.core.paginator import Paginator
from django.db.models import Count
from django.utils import timezone

from core.http import ServiceError
from microsites.models import ExamItem


def review_page(level="", section="", status="", order="", page=1):
    qs = ExamItem.objects.all()
    if level:
        qs = qs.filter(level=level)
    if section:
        qs = qs.filter(section=section)
    counts = {r["status"]: r["n"] for r in qs.values("status").annotate(n=Count("id"))}
    reported = qs.filter(reports__gt=0).count()
    if status == "reported":
        qs = qs.filter(reports__gt=0)
    elif status:
        qs = qs.filter(status=status)
    qs = qs.order_by("-reports", "level", "section", "group", "id") if order == "reports" or status == "reported" else qs.order_by("level", "section", "group", "id")
    return Paginator(qs, 15).get_page(page), counts, reported


def save(pk, data, user):
    q = ExamItem.objects.filter(pk=pk).first()
    if q is None:
        raise ServiceError("ไม่พบโจทย์นี้", status=404)
    action = data.get("action", "save")
    if action == "hide":
        q.status = ExamItem.HIDDEN
        q.save(update_fields=["status"])
        return q
    choices = [str(c).strip() for c in data.get("choices") or []]
    if len(choices) != 4 or not all(choices) or len(set(choices)) != 4:
        raise ServiceError("ต้องมีตัวเลือก 4 ข้อ ไม่ว่าง และไม่ซ้ำกัน")
    try:
        answer = int(data.get("answer"))
    except (TypeError, ValueError):
        answer = -1
    if not 0 <= answer <= 3:
        raise ServiceError("เลือกข้อที่ถูกต้อง")
    stem = str(data.get("stem", "")).strip()
    if not stem:
        raise ServiceError("โจทย์ต้องไม่ว่าง")
    q.stem, q.choices, q.answer = stem[:600], [c[:120] for c in choices], answer
    q.explanation = str(data.get("explanation", "")).strip()[:600]
    if "passage" in data:
        q.passage = str(data.get("passage", "")).strip()[:2000]
    if action == "approve":
        q.status, q.reviewed_by, q.reviewed_at, q.reports = ExamItem.APPROVED, user, timezone.now(), 0
    elif q.status == ExamItem.HIDDEN:
        q.status = ExamItem.LIVE
    q.save()
    return q
