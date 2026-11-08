"""Operational screens (moderation, tickets, migrations, slip rules, settings, renewals, payment detail)."""
from celery.result import AsyncResult
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from urllib.parse import urlencode

from backoffice.selectors import ops_selector
from backoffice.services import ops_service
from core.decorators import admin_required
from core.http import ServiceError, ajax_view, json_body, ok


def _tabs(counts, labels, current):
    return [(key, label, counts.get(key, 0)) for key, label in labels]


@admin_required
@ensure_csrf_cookie
def community(request):
    kind = "comments" if request.GET.get("kind") == "comments" else "posts"
    status = request.GET.get("status", "")
    page, counts = ops_selector.community_page(kind, status, request.GET.get("page", 1))
    labels = [("PENDING", "รอตรวจ"), ("REWRITTEN", "AI เกลาถ้อยคำ"), ("REJECTED", "ถูกปฏิเสธ"), ("APPROVED", "ผ่านแล้ว")]
    return render(request, "backoffice/ops_community.html", {
        "page": page, "kind": kind, "status": status, "tabs": _tabs(counts, labels, status), "nav": "community",
        "qs": urlencode({"kind": kind, "status": status}) + "&"})


@admin_required
@ensure_csrf_cookie
def tickets(request):
    status = request.GET.get("status", "")
    page, counts = ops_selector.tickets_page(status, request.GET.get("page", 1))
    return render(request, "backoffice/ops_tickets.html", {
        "page": page, "status": status, "nav": "tickets", "qs": urlencode({"status": status}) + "&",
        "tabs": _tabs(counts, [("pending", "รอดำเนินการ"), ("resolved", "ปิดแล้ว")], status)})


@admin_required
@ensure_csrf_cookie
def migrations(request):
    status = request.GET.get("status", "")
    page, counts = ops_selector.migrations_page(status, request.GET.get("page", 1))
    imports, stats = ops_selector.lifetime_imports_page(request.GET.get("ipage", 1), request.GET.get("q", "").strip())
    labels = [("pending", "รอดำเนินการ"), ("processing", "กำลังดำเนินการ"), ("approved", "อนุมัติ"), ("rejected", "ปฏิเสธ")]
    return render(request, "backoffice/ops_migrations.html", {
        "page": page, "status": status, "tabs": _tabs(counts, labels, status), "imports": imports, "stats": stats,
        "nav": "migrations", "qs": urlencode({"status": status}) + "&", "q": request.GET.get("q", "")})


@admin_required
@ensure_csrf_cookie
def slips(request):
    return render(request, "backoffice/ops_slips.html", {
        "rules": ops_selector.slip_rules(), "logs": ops_selector.verification_logs(request.GET.get("page", 1)), "nav": "slips", "qs": ""})


@admin_required
@ensure_csrf_cookie
def renewals(request):
    return render(request, "backoffice/ops_renewals.html", {"rows": ops_selector.renewals(), "nav": "renewals"})


@ajax_view("GET", staff=True)
def payment_detail(request, payment_id):
    data = ops_selector.payment_detail(payment_id)
    if not data:
        raise ServiceError("ไม่พบรายการชำระเงินนี้", status=404)
    return ok(data)


@ajax_view("POST", staff=True)
def moderate(request, kind, pk):
    return ok(message=ops_service.moderate(kind, pk, json_body(request).get("action")))


@ajax_view("POST", staff=True)
def ticket_action(request, pk):
    ops_service.ticket_action(pk, json_body(request).get("action"))
    return ok(message="อัปเดตคำร้องแล้ว")


@ajax_view("POST", staff=True)
def migration_action(request, pk):
    d = json_body(request)
    ops_service.migration_action(pk, d.get("action"), request.user, d.get("note", ""))
    return ok(message="อัปเดตคำขอแล้ว")


@ajax_view("POST", staff=True)
def rule_add(request):
    d = json_body(request)
    r = ops_service.add_rule(d.get("type"), d.get("pattern"), d.get("description"))
    return ok({"id": r.id}, status=201, message="เพิ่มกฎแล้ว")


@ajax_view("POST", staff=True)
def rule_delete(request, pk):
    ops_service.delete_rule(pk)
    return ok(message="ลบกฎแล้ว")


@ajax_view("POST", staff=True)
def setting_save(request):
    d = json_body(request)
    ops_service.save_setting(request.user, d.get("key"), d.get("value"))
    return ok(message="บันทึกการตั้งค่าแล้ว")


@ajax_view("POST", staff=True)
def setting_delete(request):
    ops_service.delete_setting(request.user, json_body(request).get("key"))
    return ok(message="ลบการตั้งค่าแล้ว")


@ajax_view("POST", staff=True)
def renewals_send(request):
    r = ops_service.send_renewals(json_body(request))
    if r.ready():
        d = r.get()
        return ok({"state": "done", **d}, message=f"ส่งอีเมลเตือนแล้ว สำเร็จ {d['sent']} · ล้มเหลว {d['failed']}")
    return ok({"state": "pending", "task_id": r.id}, message="กำลังส่งอีเมลเตือนเบื้องหลัง")
