"""Small cache-based limits for the free, login-less AI features (dictionary, translator).
Uses Django's cache: set CACHES to Redis in production so every worker shares the counters."""
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from core.http import ServiceError


def client_ip(request):
    meta = request.META
    return (meta.get("HTTP_CF_CONNECTING_IP") or meta.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or meta.get("REMOTE_ADDR", "") or "unknown")


def _hit(key, ttl):
    if cache.add(key, 1, ttl):
        return 1
    try:
        return cache.incr(key)
    except ValueError:      # expired between add() and incr()
        cache.set(key, 1, ttl)
        return 1


def check_ai(request, feature):
    """Raise ServiceError(429) when this visitor or the whole site used up today's AI allowance for `feature`."""
    per_hour = getattr(settings, "RYU_AI_PER_IP_HOUR", 30)
    per_day = getattr(settings, "RYU_AI_DAILY_LIMIT", 2000)
    ip = client_ip(request)
    hour = timezone.now().strftime("%Y%m%d%H")
    day = timezone.now().strftime("%Y%m%d")
    if _hit(f"ryu_ai:{feature}:ip:{ip}:{hour}", 3600) > per_hour:
        raise ServiceError("ใช้ AI ครบโควตาชั่วโมงนี้แล้ว ลองใหม่ในอีกสักครู่นะครับ", status=429)
    if _hit(f"ryu_ai:{feature}:day:{day}", 86400) > per_day:
        raise ServiceError("วันนี้มีผู้ใช้ AI ครบโควตาของระบบแล้ว ลองใหม่พรุ่งนี้นะครับ", status=429)
