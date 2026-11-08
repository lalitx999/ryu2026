"""Tiny JSON/AJAX helpers.  Views stay thin: parse -> call service -> return one of these."""
import json
from functools import wraps

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


class ServiceError(Exception):
    """Raised by services for expected, user-facing failures (maps to a 4xx JSON reply)."""

    def __init__(self, message, status=400, **extra):
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra


def ok(data=None, status=200, **extra):
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})


def fail(message, status=400, **extra):
    return JsonResponse({"ok": False, "error": message, **extra}, status=status,
                        json_dumps_params={"ensure_ascii": False})


def json_body(request):
    """Accept both application/json and form posts (multipart uploads)."""
    if request.content_type == "application/json":
        try:
            return json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return {}
    return request.POST


def ajax_view(*methods, login=False, staff=False):
    """Decorator: method guard + auth guard + ServiceError -> JSON conversion."""
    methods = methods or ("GET",)

    def decorator(func):
        @wraps(func)
        @require_http_methods(list(methods))
        def wrapper(request, *args, **kwargs):
            user = request.user
            if login and not user.is_authenticated:
                return fail("กรุณาเข้าสู่ระบบก่อนค่ะ", status=401, login_required=True)
            if staff and not (user.is_authenticated and is_admin_user(user)):
                return fail("ไม่มีสิทธิ์เข้าถึง", status=403)
            try:
                return func(request, *args, **kwargs)
            except ServiceError as exc:
                return fail(exc.message, status=exc.status, **exc.extra)

        return wrapper

    return decorator


def is_admin_user(user):
    return bool(user.is_active and (user.is_staff or user.is_superuser or getattr(user, "role", "") == "admin"))
