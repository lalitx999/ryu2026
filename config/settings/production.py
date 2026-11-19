from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # noqa: F405  (required)

# The RYU Network domains (punycode, apex + www) are answered by this same project.
from microsites.registry import all_hosts  # noqa: E402
ALLOWED_HOSTS += [h for h in all_hosts() if h not in ALLOWED_HOSTS]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_CONTENT_TYPE_NOSNIFF = True

# Static files: WhiteNoise (configured in base.py).  If Nginx serves /static/ directly,
# drop the middleware and point `alias` at STATIC_ROOT after `collectstatic`.
STORAGES["staticfiles"] = {"BACKEND": "config.storage.HashedModuleStorage"}  # noqa: F405
CELERY_TASK_ALWAYS_EAGER = False
