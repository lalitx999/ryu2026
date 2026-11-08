"""Araigogu AI page + JSON API.  Guests may chat (as before); data is scoped to who owns the session."""
from celery.result import AsyncResult
from django.core.cache import cache
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from core.http import ServiceError, ajax_view, json_body, ok
from support import tasks
from support.selectors import araigogu_selector
from support.services import araigogu_service

RATE_PER_MINUTE = 15


@ensure_csrf_cookie
def page(request):
    return render(request, "portal/araigogu.html")


def _throttle(request):
    key = f"ara:{request.user.pk or request.META.get('REMOTE_ADDR', '?')}"
    n = cache.get(key, 0)
    if n >= RATE_PER_MINUTE:
        raise ServiceError("ส่งข้อความเร็วเกินไปค่ะ รอสักครู่แล้วลองใหม่นะคะ", status=429)
    cache.set(key, n + 1, 60)


@ajax_view("POST")
def chat(request):
    _throttle(request)
    d = json_body(request)
    sess = araigogu_service.start_turn(request.user, request.session, d.get("session_id"),
                                       d.get("target_language"), d.get("mode"), d.get("message"))
    result = tasks.araigogu_reply.delay(sess.pk)
    if result.ready():  # eager mode (local dev)
        return ok({"state": "done", **result.get()})
    return ok({"state": "pending", "task_id": result.id, "session_id": sess.session_id})


@ajax_view("GET")
def result(request, task_id):
    r = AsyncResult(task_id)
    if not r.ready():
        return ok({"state": "pending"})
    if r.failed():
        return ok({"state": "done", "content": tasks.FALLBACK_REPLY, "model_used": "fallback"})
    return ok({"state": "done", **r.get()})


@ajax_view("GET")
def history(request):
    return ok(araigogu_selector.history(request.user, request.session))


@ajax_view("GET", "DELETE")
def session_detail(request, session_id):
    if request.method == "DELETE":
        araigogu_service.delete_session(request.user, request.session, session_id)
        return ok(message="ลบประวัติสนทนาเรียบร้อยแล้ว")
    data = araigogu_selector.session_detail(request.user, request.session, session_id)
    if not data:
        raise ServiceError("ไม่พบประวัติสนทนา", status=404)
    return ok(data)
