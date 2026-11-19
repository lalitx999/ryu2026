"""Admin screen: review the AI-written mock JLPT questions (วัดระดับภาษาญี่ปุ่น.online)."""
from urllib.parse import urlencode

from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import admin_required
from core.http import ajax_view, json_body, ok
from microsites.models import ExamItem
from microsites.services import exam_review


@admin_required
@ensure_csrf_cookie
def exam(request):
    g = request.GET
    level, section, status, order = g.get("level", ""), g.get("section", ""), g.get("status", ""), g.get("order", "")
    page, counts, reported = exam_review.review_page(level, section, status, order, g.get("page", 1))
    tabs = [(k, label, counts.get(k, 0)) for k, label in ExamItem.STATUS] + [("reported", "ถูกแจ้งว่าผิด", reported)]
    return render(request, "backoffice/exam.html", {
        "page": page, "level": level, "section": section, "status": status, "nav": "exam", "tabs": tabs,
        "levels": ["N5", "N4", "N3", "N2", "N1"], "sections": ExamItem.SECTIONS,
        "qs": urlencode({"level": level, "section": section, "status": status, "order": order}) + "&"})


@ajax_view("POST", staff=True)
def exam_save(request, pk):
    q = exam_review.save(pk, json_body(request), request.user)
    label = dict(ExamItem.STATUS)[q.status]
    return ok({"status": q.status, "label": label}, message=f"บันทึกแล้ว ({label})")
