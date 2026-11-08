"""Settings shared by every environment.  Secrets come from the environment / .env only."""
import sys
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "apps"))  # apps are imported by label: users, courses, ...

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")  # no default on purpose: fail loudly if it is missing
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SITE_URL = env("SITE_URL", default="http://127.0.0.1:8000")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # project apps (labels kept identical to the legacy DB / migrations)
    "core.apps.CoreConfig",
    "users.apps.UsersConfig",
    "courses.apps.CoursesConfig",
    "payments.apps.PaymentsConfig",
    "quizzes.apps.QuizzesConfig",
    "affiliates.apps.AffiliatesConfig",
    "support.apps.SupportConfig",
    "system_config.apps.SystemConfigConfig",
    "community.apps.CommunityConfig",
    "portal.apps.PortalConfig",
    "backoffice.apps.BackofficeConfig",
]
# NOTE: django.contrib.admin is intentionally NOT installed - end users get the custom
# Bootstrap dashboard in `backoffice` instead (rule #4).

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME", default="ryuclass_db"),
        "USER": env("DB_USER", default="root"),
        "PASSWORD": env("DB_PASS", default=""),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env("DB_PORT", default="3306"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET time_zone='+07:00', sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = ["users.backends.EmailBackend"]
LOGIN_URL = "/"  # login happens in the XP modal on the desktop
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
]

LANGUAGE_CODE = "th"
TIME_ZONE = "Asia/Bangkok"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Private uploads live outside STATIC_ROOT and are only served through authorised views.
SLIPS_STORAGE_DIR = env("SLIPS_STORAGE_DIR", default=str(BASE_DIR / "storage" / "slips"))
PDF_STORAGE_DIR = env("PDF_STORAGE_DIR", default=str(BASE_DIR / "storage" / "protected_pdfs"))
COMMUNITY_STORAGE_DIR = env("COMMUNITY_STORAGE_DIR", default=str(BASE_DIR / "storage" / "community"))
MEDIA_ROOT = PDF_STORAGE_DIR
MEDIA_URL = "/storage/protected_pdfs/"
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
MAX_SLIP_BYTES = 8 * 1024 * 1024

# Sessions replace the legacy JWT: pure Django, cookie based, works with plain AJAX + CSRF.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # ajax.js reads the cookie for X-CSRFToken

# ── Business config ─────────────────────────────────
AES_KEY = env("AES_KEY", default="")
AES_IV = env("AES_IV", default="")
RENEWAL_BONUS_DAYS = env.int("RENEWAL_BONUS_DAYS", default=3)
EASYSLIP_API_KEY = env("EASYSLIP_API_KEY", default="")
MERCHANT_ACCOUNT_NUMBER = env("MERCHANT_ACCOUNT_NUMBER", default="")
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_ADMIN_CHAT_ID = env("TELEGRAM_ADMIN_CHAT_ID", default="")
DEEPSEEK_API_KEY = env("DEEPSEEK_API_KEY", default="")
DEEPSEEK_MODEL = env("DEEPSEEK_MODEL", default="deepseek-chat")
GROQ_API_KEY = env("GROQ_API_KEY", default="")
GROQ_MODEL = env("GROQ_MODEL", default="openai/gpt-oss-20b")

# ── Email ───────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="RyuClass <support@chatbotth.me>")

# ── Celery ──────────────────────────────────────────
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://127.0.0.1:6379/1")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TIME_LIMIT = 120
CELERY_RESULT_EXPIRES = 3600

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# Daily renewal reminders (needs `celery -A config beat` alongside the worker)
from celery.schedules import crontab  # noqa: E402
CELERY_BEAT_SCHEDULE = {
    "renewal-reminders": {"task": "courses.tasks.send_renewal_reminders", "schedule": crontab(hour=9, minute=0)},
}
