# HealBytes Backend

Django + DRF backend covering: Doctor/Patient auth, patient registration,
invitation codes, medications & reminders, daily check-ins, alerts, QR
verification, and in-app notifications, for the AI-Based Autonomous
Healthcare Coordination and Follow-up Agent.

This directory is self-contained and does not modify anything outside
`backend/` (frontend, AI engine, or shared infra are owned by other
team members).

## Stack

Python 3.10+, Django 5, DRF, SimpleJWT, Celery + Celery Beat (django-celery-beat,
database-backed schedule), Redis (broker + cache), drf-spectacular, Gunicorn,
SQLite (dev) / PostgreSQL (prod).

## Project layout

```
backend/
  config/
    settings/{base,dev,prod,test}.py
    urls.py, celery.py, wsgi.py, asgi.py
  apps/
    core/            shared base models, permissions, exception handler
    accounts/         Doctor/Patient auth (custom User, JWT)
    patients/         Patient profile + caretaker details, analytics
    invitations/      Invitation code generate/redeem
    medications/       Medication + reminder scheduling (Celery Beat)
    checkins/           Daily check-ins + AI-engine stub integration
    alerts/            Alert model + routing rules
    qr/                 QR token generate/verify
    notifications/     In-app notification records
  manage.py, requirements.txt, Dockerfile, .env.example
```

## Setup (local dev, SQLite)

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # adjust as needed
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API docs: `/api/docs/` (Swagger UI), `/api/redoc/`, raw schema at `/api/schema/`.

## Running Celery (reminders, AI hand-off, alert routing)

Requires Redis running locally (`redis-server`, or via the shared docker-compose
once the infra teammate provides it).

```bash
celery -A config worker -l info
celery -A config beat -l info   # dispatches medication reminders every minute
```

## Tests

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test apps
```

55 tests covering auth, invitation generation/redemption (incl. 15-min
expiry), patient scoping/permissions, medication CRUD + reminder dispatch
(+ patient email), AI client response parsing (valid/invalid/timeout), check-in
submission + full notification fan-out per the table above, alert
acknowledge/resolve, QR generate/verify (incl. 15-min expiry + wrong-doctor
rejection), and the email audit-log endpoints.

## Business-rule defaults (flagged for review)

- **Invitation codes** (`apps/invitations/models.py`): 8-char alphanumeric,
  single-use, expire after `INVITATION_CODE_EXPIRY_MINUTES` (default **15 min**).
- **QR tokens** (`apps/qr/tokens.py`): signed JWT (HS256, `SECRET_KEY`),
  identifies one patient, expires after `QR_TOKEN_EXPIRY_MINUTES` (default **15 min**).
  Verified server-side on scan; only the assigned doctor may redeem it.
- **AI engine contract** (`apps/checkins/ai_client.py`): `POST {AI_ENGINE_URL}/analyze/`
  → `{"riskLevel": "low"|"medium"|"high", "riskScore": 0.0-1.0, "reason": str,
  "recommendedAction": str, "notificationRecipient": str}`. Stored on
  `DailyCheckin` as `ai_risk_level`, `ai_risk_score`, `ai_notes` (= reason),
  `ai_recommended_action`, `ai_notification_recipient`. If `AI_ENGINE_URL` is
  unset, the call fails/times out, or the response is malformed, the check-in
  still saves with `ai_risk_level="unavailable"` and no alert/email fires.
  **`notificationRecipient` is informational/logged only** - the backend
  always decides actual routing itself via risk level (see below), so the
  two systems can never disagree about who gets notified.
- **Alert routing & notifications** (`apps/alerts/rules.py`) - the in-app
  Alert, the doctor email, the caretaker email, and the patient's own-result
  email are four independent mechanisms, each gated by its own rule function,
  because their trigger conditions don't line up 1:1:

  | AI risk  | In-app Alert (doctor dashboard) | Doctor email | Caretaker email | Patient result email |
  |----------|----------------------------------|---------------|-------------------|------------------------|
  | high     | yes (doctor + caretaker)         | **yes**       | no                | yes |
  | medium   | yes (doctor)                     | no            | **yes**           | yes |
  | low      | no                               | no            | **yes**           | yes |
  | unavailable/pending | no                    | no            | no                | no |

  Doctor email is deliberately HIGH-only so the doctor isn't inundated with
  email for every moderate check-in - medium still shows up on their
  dashboard via `/api/alerts/`. Caretaker email is deliberately LOW/MEDIUM
  only - high-risk stays an urgent doctor-facing case instead. The patient
  always gets emailed their own result (reason + recommended action) except
  when the AI engine didn't return a verdict.
- **Caretaker**: no login/dashboard of their own (not in scope) - just
  `caretaker_name` + `caretaker_email` fields captured when the doctor adds
  a patient.
- **Email audit trail**: every outbound email (doctor, patient, or
  caretaker; alert, check-in result, or medication reminder), sent or
  failed, is logged in `EmailNotificationLog` -
  `/api/notifications/email-logs/` (doctor, scoped to their patients) and
  `/api/notifications/email-logs/me/` (patient, their own only).
- **Email backend**: `django.core.mail.backends.console.EmailBackend` by
  default (dev/hackathon) - emails are fully composed and printed to the
  server console/log, not actually delivered. Switch to real SMTP by setting
  `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` plus
  `EMAIL_HOST`/`EMAIL_PORT`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`/`EMAIL_USE_TLS`
  in `.env` - no code changes needed. All sends go through Celery
  (`apps/notifications/tasks.py`), never inline in the request/response cycle.

## API areas

`/api/auth/`, `/api/patients/`, `/api/invitations/`, `/api/medications/`,
`/api/checkins/`, `/api/alerts/`, `/api/qr/`, `/api/notifications/`,
`/api/analytics/` — full detail in `/api/docs/`.
