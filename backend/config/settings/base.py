"""
Base Django settings for the Healthcare Coordination backend.
Shared by dev.py and prod.py.
"""
import os
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# python-dotenv is already a declared dependency (requirements.txt) but was
# never actually wired up, so backend/.env was silently ignored by
# `manage.py runserver`/etc. and every os.environ.get() below always fell
# back to its default. load_dotenv() only fills in variables not already
# set in the real environment, so this is a no-op wherever env vars are
# supplied another way (e.g. docker-compose's `environment:` block in prod).
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_celery_beat",
    # local apps
    "apps.core",
    "apps.accounts",
    "apps.patients",
    "apps.invitations",
    "apps.medications",
    "apps.checkins",
    "apps.alerts",
    "apps.qr",
    "apps.notifications",
    "apps.medical_history",
    "apps.appointments",
    "apps.labtests",
    "apps.documents",
]

MIDDLEWARE = [
    "apps.core.middleware.SimpleCorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- Django REST Framework ----
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

# ---- SimpleJWT ----
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_MIN", 30))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", 7))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---- drf-spectacular ----
SPECTACULAR_SETTINGS = {
    "TITLE": "Healthcare Coordination & Follow-up Agent API",
    "DESCRIPTION": "Backend APIs for Doctor/Patient auth, invitations, medications, "
                    "check-ins, alerts, QR verification and notifications.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Several models have their own `status` field with different choice
    # sets (Alert, Appointment, LabTestRequest) - name them explicitly so
    # drf-spectacular doesn't fall back to auto-generated Status178Enum-style names.
    "ENUM_NAME_OVERRIDES": {
        "AlertStatusEnum": "apps.alerts.models.Alert.Status",
        "AppointmentStatusEnum": "apps.appointments.models.Appointment.Status",
        "LabTestRequestStatusEnum": "apps.labtests.models.LabTestRequest.Status",
    },
}

# ---- Celery ----
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_BEAT_SCHEDULE = {
    "dispatch-due-medication-reminders": {
        "task": "apps.medications.tasks.dispatch_due_medication_reminders",
        "schedule": 60.0,  # every minute
    },
    "flag-missing-daily-checkins": {
        "task": "apps.checkins.tasks.flag_missing_daily_checkins",
        # Once daily, in the evening - gives patients the full day to submit
        # before being flagged as awaiting data. See apps.checkins.tasks
        # docstring: never assigns a risk level, only raises a doctor-facing
        # notification.
        "schedule": crontab(hour=21, minute=0),
    },
}

# ---- Cache (Redis) ----
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# ---- AI Engine integration (stub contract, see apps.checkins.ai_client) ----
AI_ENGINE_URL = os.environ.get("AI_ENGINE_URL", "")
AI_ENGINE_TIMEOUT_SECONDS = int(os.environ.get("AI_ENGINE_TIMEOUT_SECONDS", 8))

# ---- Business-rule defaults (see apps.alerts.rules) ----
INVITATION_CODE_EXPIRY_MINUTES = int(os.environ.get("INVITATION_CODE_EXPIRY_MINUTES", 15))
QR_TOKEN_EXPIRY_MINUTES = int(os.environ.get("QR_TOKEN_EXPIRY_MINUTES", 15))
# How long a non-assigned doctor's QR-derived consulting access (QRAccessGrant)
# stays valid after a successful scan, before it must be re-verified with a
# fresh QR code. Deliberately separate from QR_TOKEN_EXPIRY_MINUTES: the QR
# *token* is single-use-short-lived (15 min) so it can't be screenshotted and
# replayed later, but the *access it grants* to a consulting doctor needs to
# outlast that scan long enough for one consultation (default 24h).
QR_ACCESS_GRANT_HOURS = int(os.environ.get("QR_ACCESS_GRANT_HOURS", 24))

# ---- Email (caretaker notifications) ----
# Defaults to the console backend (emails are composed + logged, not sent)
# until real SMTP credentials are supplied via env vars - no code changes
# needed to switch over, just set EMAIL_BACKEND + the EMAIL_* vars below.
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@healbytes.local")
