"""Read-only health/configuration report (never returns secret values - only whether they are set)."""
import os
import shutil

from django.conf import settings
from django.db import connection


def _dir_info(path):
    if not os.path.isdir(path):
        return {"path": str(path), "exists": False, "files": 0, "size_mb": 0}
    total = count = 0
    for root, _, names in os.walk(path):
        for n in names:
            count += 1
            total += os.path.getsize(os.path.join(root, n))
    return {"path": str(path), "exists": True, "files": count, "size_mb": round(total / 1048576, 1)}


def _redis_ok():
    try:
        import redis
        redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=1).ping()
        return True
    except Exception:
        return False


def status():
    return {
        "database": {"engine": connection.vendor, "name": str(connection.settings_dict.get("NAME"))},
        "debug": settings.DEBUG,
        "email": {"host": settings.EMAIL_HOST or "(console backend)", "port": settings.EMAIL_PORT,
                  "tls": getattr(settings, "EMAIL_USE_TLS", False), "sender": settings.DEFAULT_FROM_EMAIL,
                  "configured": bool(settings.EMAIL_HOST_USER)},
        "celery": {"eager": getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False), "broker_up": _redis_ok()},
        "keys": [("EasySlip (ตรวจสลิปอัตโนมัติ)", bool(getattr(settings, "EASYSLIP_API_KEY", ""))),
                 ("Telegram (แจ้งเตือนสลิป)", bool(getattr(settings, "TELEGRAM_BOT_TOKEN", ""))),
                 ("DeepSeek (AI หลัก)", bool(settings.DEEPSEEK_API_KEY)), ("Groq (AI สำรอง)", bool(settings.GROQ_API_KEY)),
                 ("AES video key", bool(getattr(settings, "AES_KEY", "")))],
        "storage": {"slips": _dir_info(settings.SLIPS_STORAGE_DIR), "pdfs": _dir_info(settings.PDF_STORAGE_DIR),
                    "community": _dir_info(settings.COMMUNITY_STORAGE_DIR),
                    "disk_free_gb": round(shutil.disk_usage(settings.BASE_DIR).free / 1073741824, 1)},
        "site_url": settings.SITE_URL,
    }
