"""Admin screen: review the AI-drafted Thai content of RYU KANJI (คันจิ.online)."""
from urllib.parse import urlencode

from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import admin_required
from core.http import ajax_view, json_body, ok
from microsites.models import Kanji
from microsites.services import kanji_review
from microsites.tasks import draft_kanji_thai

STATUS_LABELS = [(Kanji.AI_DRAFT, "ร่าง AI รอตรวจ"), (Kanji.AI_APPROVED, "ตรวจแล้ว"), (Kanji.AI_NONE, "ยังไม่มีภาษาไทย")]


@admin_required
@ensure_csrf_cookie
def kanji(request):
    level, status, q = request.GET.get("level", ""), request.GET.get("status", ""), request.GET.get("q", "").strip()
    page, counts = kanji_review.review_page(level, status, q, request.GET.get("page", 1))
    for k in page:
        k.examples_text = "\n".join(f'{e.get("word", "")} | {e.get("reading", "")} | {e.get("th", "")}' for e in k.examples or [])
    return render(request, "backoffice/kanji.html", {
        "page": page, "level": level, "status": status, "q": q, "nav": "kanji",
        "levels": ["N5", "N4", "N3", "N2", "N1"], "tabs": [(k, label, counts.get(k, 0)) for k, label in STATUS_LABELS],
        "qs": urlencode({"level": level, "status": status, "q": q}) + "&"})


@ajax_view("POST", staff=True)
def kanji_save(request, pk):
    k = kanji_review.save(pk, json_body(request), request.user)
    return ok({"ai_status": k.ai_status}, message="อนุมัติแล้ว" if k.ai_status == Kanji.AI_APPROVED else "บันทึกแล้ว")


@ajax_view("POST", staff=True)
def kanji_ai_draft(request):
    body = json_body(request)
    level = body.get("level") if body.get("level") in ("N5", "N4", "N3", "N2", "N1") else None
    task = draft_kanji_thai.delay(level, 24)
    return ok({"task_id": task.id}, message="ส่งงานให้ AI ร่างคันจิ 24 ตัวถัดไปแล้ว รีเฟรชหน้านี้ในอีกสักครู่")
