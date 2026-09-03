from .base import *  # noqa

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# base.py now loads backend/.env (see base.py) so local dev config doesn't
# leak into test runs regardless of what's in that file - tests must stay
# isolated and deterministic (AI engine "unavailable" by default, as the
# existing tests assume).
AI_ENGINE_URL = ""
