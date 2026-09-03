from .base import *  # noqa

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

CORS_ALLOW_ALL_ORIGINS = True

# `npm run dev` does not start Redis or a Celery worker (see root
# package.json). Rather than requiring that extra local infrastructure,
# run Celery tasks (AI analysis, alert routing, notification emails)
# synchronously in-process for local dev - the same mechanism the project
# already uses for tests (config/settings/test.py). Celery itself, the task
# definitions, and production behavior (config/settings/prod.py) are
# unchanged; only local-dev execution timing changes.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
