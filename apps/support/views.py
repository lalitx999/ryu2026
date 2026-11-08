from celery.result import AsyncResult
from django.core.cache import cache

from core.http import ServiceError, ajax_view, json_body, ok
from support import tasks


@ajax_view("POST")
def chat_send(request):
    ip = request.META.get("REMOTE_ADDR", "?")
    key = f"chat:{request.user.pk or ip}"
    count = cache.get(key, 0)
    if count >= 20:
        raise ServiceError("ถามเร็วเกินไปค่ะ รอสักครู่แล้วลองใหม่นะคะ", status=429)
    cache.set(key, count + 1, 60)
    data = json_body(request)
    messages = data.get("messages") or []
    if not isinstance(messages, list) or not messages:
        raise ServiceError("ไม่มีข้อความ")
    ctx = data.get("lesson_context") or {}
    result = tasks.chat_reply.delay(messages, ctx.get("lesson_title", ""), ctx.get("course_level", ""))
    if result.ready():  # eager mode (local dev) answers immediately
        return ok({"state": "done", **result.get()})
    return ok({"state": "pending", "task_id": result.id})


@ajax_view("GET")
def chat_result(request, task_id):
    result = AsyncResult(task_id)
    if not result.ready():
        return ok({"state": "pending"})
    if result.failed():
        return ok({"state": "done", "reply": "AIRIS ติดต่อบริการ AI ไม่ได้ในขณะนี้ค่ะ ลองใหม่อีกครั้งนะคะ 💖"})
    return ok({"state": "done", **result.get()})
