from urllib.parse import urlencode

import csv

from celery.result import AsyncResult
from django.contrib.auth import login
from django.http import Http404, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

from backoffice.selectors import admin_selector
from backoffice import tasks
from backoffice.selectors import system_selector
from backoffice.services import admin_service, course_admin_service as cs, user_admin_service as us
from courses.models import Lesson, Module
from core.decorators import admin_required
from core.http import ServiceError, ajax_view, is_admin_user, json_body, ok


@ensure_csrf_cookie
def login_page(request):
    if request.user.is_authenticated and is_admin_user(request.user):
        return redirect("backoffice:dashboard")
    return render(request, "backoffice/login.html")


@ajax_view("POST")
def login_api(request):
    from core.http import ServiceError
    from users.services import auth_service

    data = json_body(request)
    user = auth_service.login_user(data.get("email"), data.get("password"))
    if not is_admin_user(user):
        raise ServiceError("บัญชีของคุณไม่มีสิทธิ์การใช้งานฝั่งผู้ดูแลระบบ (Staff/Admin Only)", status=403)
    login(request, user, backend="users.backends.EmailBackend")
    return ok({"next": "/admin-panel/"})


@admin_required
@ensure_csrf_cookie
def dashboard(request):
    return render(request, "backoffice/dashboard.html", {"d": admin_selector.dashboard(), "nav": "dashboard"})


@admin_required
@ensure_csrf_cookie
def payments(request):
    per_page = admin_selector.page_size(request.GET.get("per_page"))
    page, counts = admin_selector.payments_page(request.GET.get("status", ""), request.GET.get("q", "").strip(),
                                               request.GET.get("page", 1), per_page)
    status = request.GET.get("status", "")
    tabs = [("", "ทั้งหมด", sum(counts.values())), ("pending", "รอตรวจ", counts["pending"]),
            ("approved", "อนุมัติแล้ว", counts["approved"]), ("rejected", "ปฏิเสธ", counts["rejected"])]
    q = request.GET.get("q", "")
    return render(request, "backoffice/payments.html", {
        "page": page, "tabs": tabs, "status": status, "q": q, "nav": "payments", "per_page": per_page,
        "sizes": admin_selector.PAGE_SIZES, "qs": urlencode({"status": status, "q": q, "per_page": per_page}) + "&"})


@admin_required
@ensure_csrf_cookie
def users(request):
    per_page = admin_selector.page_size(request.GET.get("per_page"))
    page = admin_selector.users_page(request.GET.get("q", "").strip(), request.GET.get("role", ""),
                                     request.GET.get("page", 1), per_page)
    q, role = request.GET.get("q", ""), request.GET.get("role", "")
    from courses.models import Course
    return render(request, "backoffice/users.html", {
        "page": page, "q": q, "role": role, "nav": "users", "per_page": per_page, "sizes": admin_selector.PAGE_SIZES,
        "qs": urlencode({"q": q, "role": role, "per_page": per_page}) + "&",
        "courses": Course.objects.only("id", "title", "level").order_by("sort_order", "id")})


@admin_required
@ensure_csrf_cookie
def courses(request):
    return render(request, "backoffice/courses.html", {"courses": admin_selector.courses_list(), "nav": "courses"})


@admin_required
@ensure_csrf_cookie
def course_edit(request, course_id):
    course = admin_selector.course_detail(course_id)
    if not course:
        raise Http404
    lessons = {l.id: {"id": l.id, "module_id": l.module_id, "title": l.title, "description": l.description or "",
                      "video_url": l.video_url or "", "duration": l.duration, "pdf_title": l.pdf_title or "",
                      "is_free": l.is_free} for m in course.modules.all() for l in m.lessons.all()}
    return render(request, "backoffice/course_edit.html", {"course": course, "lessons_data": lessons, "nav": "courses"})


@admin_required
@ensure_csrf_cookie
def broadcast_page(request):
    from courses.models import Course
    return render(request, "backoffice/broadcast.html", {"nav": "broadcast", "courses": Course.objects.only("id", "title", "level").order_by("sort_order", "id")})


@admin_required
def sales(request):
    return render(request, "backoffice/sales.html", {"r": admin_selector.sales_report(), "nav": "sales"})


@admin_required
def analytics(request):
    return render(request, "backoffice/analytics.html", {"a": admin_selector.analytics(), "nav": "analytics"})


@admin_required
def roles(request):
    matrix = [("เรียนคอร์สตามสิทธิ์ ทำแบบทดสอบ", True, True), ("ใช้ชุมชน เกม และ Araigogu AI", True, True),
              ("เข้าหลังบ้าน (/admin-panel/)", False, True), ("ตรวจและอนุมัติสลิปชำระเงิน", False, True),
              ("จัดการคอร์ส หมวด และบทเรียน", False, True), ("จัดการนักเรียนและสิทธิ์รายคอร์ส", False, True),
              ("บรอดแคสต์อีเมล / ดูรายงานยอดขาย", False, True), ("ดูสถานะตั้งค่าระบบ", False, True)]
    return render(request, "backoffice/roles.html", {"o": admin_selector.roles_overview(), "matrix": matrix, "nav": "roles"})


@admin_required
def settings_page(request):
    from backoffice.selectors import ops_selector
    return render(request, "backoffice/settings.html", {"s": system_selector.status(), "nav": "settings",
                                                       "rows": ops_selector.settings_rows(), "is_super": request.user.is_superuser})


# ── AJAX actions ───────────────────────────────────────────
@ajax_view("POST", staff=True)
def review_payment(request, payment_id):
    data = json_body(request)
    p = admin_service.review_payment(payment_id, request.user, data.get("action"), data.get("reason", ""))
    return ok({"status": p.status}, message="อนุมัติสิทธิ์การเรียนเรียบร้อย" if p.status == "approved" else "ปฏิเสธรายการแล้ว")


@ajax_view("POST", staff=True)
def update_course(request, course_id):
    c = cs.save_course(json_body(request), course_id)
    return ok({"id": c.id}, message="บันทึกคอร์สเรียบร้อย")


@ajax_view("POST", staff=True)
def create_course(request):
    c = cs.save_course(json_body(request))
    return ok({"id": c.id}, status=201, message="สร้างคอร์สเรียนใหม่เรียบร้อยแล้ว")


@ajax_view("POST", staff=True)
def delete_course(request, course_id):
    cs.delete_course(course_id)
    return ok(message="ลบคอร์สเรียบร้อยแล้ว")


@ajax_view("POST", staff=True)
def save_module(request, module_id=None):
    m = cs.save_module(json_body(request), module_id)
    return ok({"id": m.id, "title": m.title}, status=200 if module_id else 201, message="บันทึกหมวดเรียบร้อย")


@ajax_view("POST", staff=True)
def delete_module(request, module_id):
    cs.delete_module(module_id)
    return ok(message="ลบหมวดเรียบร้อยแล้ว")


@ajax_view("POST", staff=True)
def save_lesson(request, lesson_id=None):
    data = json_body(request)
    l = cs.save_lesson(data, request.FILES, lesson_id)
    return ok({"id": l.id}, status=200 if lesson_id else 201, message="บันทึกบทเรียนเรียบร้อย")


@ajax_view("POST", staff=True)
def sort_module_lessons(request, module_id):
    n = cs.sort_lessons_by_number(module_id)
    return ok({"count": n}, message=f"จัดเรียงลำดับบทเรียน 1..{n} ตามเลขหน้าชื่อบทเรียบร้อยแล้ว")


@ajax_view("POST", staff=True)
def delete_lesson(request, lesson_id):
    cs.delete_lesson(lesson_id)
    return ok(message="ลบบทเรียนเรียบร้อยแล้ว")


@ajax_view("POST", staff=True)
def reorder(request, kind):
    model = {"modules": Module, "lessons": Lesson}.get(kind)
    if not model:
        raise ServiceError("ไม่รู้จักประเภทที่จะจัดเรียง")
    cs.reorder(model, json_body(request).get("ids"))
    return ok(message="จัดเรียงลำดับเรียบร้อยแล้ว")


@ajax_view("GET", staff=True)
def user_detail(request, user_id):
    data = admin_selector.user_detail(user_id)
    if not data:
        raise ServiceError("ไม่พบรายชื่อผู้เรียนนี้", status=404)
    return ok(data)


@ajax_view("POST", staff=True)
def create_user(request):
    u, password = us.create_user(json_body(request))
    return ok({"id": u.id, "email": u.email, "password_used": password}, status=201, message="เพิ่มนักเรียนใหม่เข้าระบบเรียบร้อยแล้ว")


@ajax_view("POST", staff=True)
def update_user(request, user_id):
    u = us.update_user(user_id, request.user, json_body(request))
    return ok({"id": u.id}, message="บันทึกข้อมูลผู้ใช้เรียบร้อย")


@ajax_view("POST", staff=True)
def import_users(request):
    rows = json_body(request).get("students")
    if not isinstance(rows, list) or not rows:
        raise ServiceError("กรุณาระบุรายการนักเรียน")
    if len(rows) > 5000:
        raise ServiceError("นำเข้าได้ครั้งละไม่เกิน 5,000 แถว")
    result = tasks.import_students.delay(rows)
    if result.ready():
        return ok({"state": "done", **result.get()})
    return ok({"state": "pending", "task_id": result.id})


@ajax_view("GET", staff=True)
def task_result(request, task_id):
    r = AsyncResult(task_id)
    if not r.ready():
        return ok({"state": "pending"})
    if r.failed():
        raise ServiceError("งานนำเข้าล้มเหลว กรุณาลองใหม่", status=500)
    return ok({"state": "done", **r.get()})


@ajax_view("POST", staff=True)
def broadcast(request):
    data = json_body(request)
    n = admin_service.broadcast(data.get("subject"), data.get("message"), data.get("target") or data.get("target_role", "all"))
    return ok({"total": n}, message=f"กำลังส่งอีเมลถึง {n} รายชื่อ (ส่งเบื้องหลัง)")


class _Echo:
    def write(self, value):
        return value


@admin_required
def export_payments(request):
    """CSV download streamed row by row (UTF-8 BOM so Excel shows Thai correctly)."""
    header = ["id", "email", "name", "course", "duration_days", "amount", "status", "type", "trans_ref", "submitted_at", "reviewed_at"]
    writer = csv.writer(_Echo())

    def rows():
        yield "\ufeff" + writer.writerow(header)
        for r in admin_selector.payments_csv_rows():
            yield writer.writerow(r)

    resp = StreamingHttpResponse(rows(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="payments.csv"'
    return resp
