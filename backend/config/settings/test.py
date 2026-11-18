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
AI_ENGINE_INTERNAL_KEY = ""

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "healbytes-test-cache",
    }
}

# Keep rate throttling active in the stack while using high defaults for test
# suites; dedicated throttle tests override these rates explicitly.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        "auth_login": "1000/minute",
        "auth_register": "1000/minute",
        "auth_refresh": "1000/minute",
        "invitation_redeem": "1000/minute",
    },
}
