import os

from celery.result import AsyncResult
from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from core.http import ServiceError, ajax_view, json_body, ok
from community import tasks
from community.selectors import post_selector
from community.services import post_service

CATEGORY_TABS = [("ALL", "ทั้งหมด"), ("QNA", "❓ ถาม-ตอบ"), ("TECHNIQUE", "💡 แชร์เทคนิค"),
                 ("JAPAN_EXP", "✈️ ประสบการณ์"), ("GENERAL", "🎌 พูดคุยทั่วไป")]
EMOJIS = ["😀", "😂", "🥰", "😎", "🤔", "😭", "🙏", "👍", "🔥", "💯", "✨", "🎌", "🇯🇵", "📚", "✍️", "🍣", "🍜", "🌸", "⛩️", "🗻"]


@ensure_csrf_cookie
def forum_page(request):
    return render(request, "portal/community.html", {"tabs": CATEGORY_TABS, "emojis": EMOJIS})


@ensure_csrf_cookie
def post_page(request, post_id):
    post = post_selector.post_detail(request.user, post_id)
    if not post:
        raise Http404
    if post["moderation_status"] != "PENDING":
        post_service.bump_views(post_id)
        post["views_count"] += 1
    return render(request, "portal/community_post.html", {"post": post})


@ajax_view("GET", "POST")
def posts(request):
    if request.method == "GET":
        return ok(post_selector.post_list(request.user, request.GET.get("category", ""),
                                          (request.GET.get("search") or "").strip()[:100]))
    if not request.user.is_authenticated:
        raise ServiceError("กรุณาเข้าสู่ระบบก่อนตั้งกระทู้ค่ะ", status=401, login_required=True)
    data = json_body(request)
    post = post_service.create_post(request.user, data.get("category"), data.get("title"),
                                    data.get("content"), request.FILES.getlist("images"))
    # create_post commits its own transaction, so the worker is guaranteed to see the row
    return _task_reply(tasks.moderate_post.delay(post.id), post.id)


def _task_reply(result, obj_id):
    if result.ready():
        return ok({"state": "done", **result.get()}, status=201)
    return ok({"state": "pending", "task_id": result.id, "id": obj_id}, status=202)


@ajax_view("GET", login=True)
def moderation_result(request, task_id):
    result = AsyncResult(task_id)
    if not result.ready():
        return ok({"state": "pending"})
    if result.failed():
        return ok({"state": "done", "status": "APPROVED", "reason": ""})
    return ok({"state": "done", **result.get()})


@ajax_view("POST", login=True)
def like(request, post_id):
    return ok(post_service.toggle_like(request.user, post_id))


@ajax_view("POST", login=True)
def comment(request, post_id):
    c = post_service.add_comment(request.user, post_id, json_body(request).get("content"))
    return _task_reply(tasks.moderate_comment.delay(c.id), c.id)


def community_image(request, filename):
    path = os.path.join(settings.COMMUNITY_STORAGE_DIR, os.path.basename(filename))
    if not os.path.isfile(path):
        raise Http404
    return FileResponse(open(path, "rb"))
