from .base import *  # noqa: F401,F403
import environ

DEBUG = True
ALLOWED_HOSTS = ["*"]
SECRET_KEY = env("SECRET_KEY", default="dev-only-insecure-key")  # noqa: F405

# Developing without Redis: run Celery tasks inline in the request.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)  # noqa: F405
CELERY_TASK_EAGER_PROPAGATES = True

# Print mails to the console unless SMTP creds are configured.
if not EMAIL_HOST_USER:  # noqa: F405
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Optional: DB_ENGINE=sqlite lets you smoke-test the UI on a machine without MySQL.
if env("DB_ENGINE", default="mysql") == "sqlite":  # noqa: F405
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}  # noqa: F405
    # Some legacy migrations contain raw MySQL SQL; for a throw-away SQLite DB build tables straight from the models.
    MIGRATION_MODULES = {a: None for a in ("users", "courses", "payments", "quizzes", "affiliates", "support",
                                           "system_config", "community")}
