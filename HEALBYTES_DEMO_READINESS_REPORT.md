# HealBytes — Demo Readiness Report

Scope note: QR code / QR scanner functionality was explicitly excluded per instructions and was not touched or investigated.

## 1. Root Causes

**Doctor patient search was fake.** `pages/doctor/Patients.jsx` never called a backend search endpoint — it filtered whatever page of patients happened to load once at mount, entirely client-side. A real, working search pattern already existed for receptionists (`/patients/search/`), but the doctor list endpoint (`/patients/`) had no search parameter at all.

**Patient dashboard/profile silently broke for real (non-demo) patients.** `DataContext` only ever live-fetched patient data for role `DOCTOR`. A patient logging in normally (not immediately after redeeming an invitation) had no own `Patient` record in state — `condition`, `riskLevel`, `caretaker`, etc. all rendered as `undefined`/blank.

**Every check-in submission double-posted.** `DataContext.submitCheckin` called both `submitCheckinApi` and `analyzeCheckinAI`, and in live mode both hit the exact same `POST /checkins/` endpoint — one check-in submission created two rows server-side. Underlying this was a deeper mismatch: the backend computes the AI risk verdict *after* the check-in is saved (via a Celery task), so the create response never contained risk data in the first place — the frontend's synchronous "submit → get AI result" assumption didn't match how the backend actually works.

**Medication "mark as taken" never persisted.** Both the mock and live branches of `markMedicationStatus` just returned a locally-constructed object — no backend call existed at all, despite a real acknowledge endpoint (`/medications/reminders/:id/acknowledge/`) being available.

**Appointments were two disconnected systems.** The doctor's "Schedule Follow-up" action only updated a local `nextFollowUp` field on the frontend's Patient object — never touched the backend `Appointment` model. Meanwhile there was no patient-facing appointments UI at all (no route, no nav entry), and appointment creation on the backend never notified anyone.

**Notifications had no UI for 3 of 4 roles.** The backend has been correctly creating `Notification` rows for medication reminders, lab results, alerts, and invitations the whole time — but the frontend only ever read that endpoint from the Lab Technician layout. Doctor, Patient, and Receptionist had no bell, no badge, no list.

**Alerts (AI insights) were stale/session-local even against a real backend.** `GET /alerts/` was defined but never called — "Recent AI Insights" and the doctor/patient Alerts pages only showed demo-seeded data or alerts generated client-side during the current browser session.

**Alert resolution was silently broken.** The frontend sent `PUT /alerts/:id/resolve/`; the backend view only implements `POST`. Every resolve attempt in live mode would have 405'd.

**Two dead API files were live landmines.** `src/api/reception.api.js` and the original `src/api/appointment.api.js` called endpoints that never existed anywhere in the Django backend (`/reception/patients`, `/appointments/slots`, `/patients/:id/appointments`). Neither was imported by any active page, so they never actually broke anything at runtime — but either would 404 immediately if someone reconnected them.

**Error handling was mostly `console.error` and nothing else.** Several screens (patient Lab Results, the check-in flow, `Topbar`'s decorative search box) either had no user-facing error state, or — worse — collapsed "fetch failed" and "genuinely empty" into the same indistinguishable empty-state UI.

## 2. Fixes Made

**Backend**
- `apps/patients/views.py` — added `?search=` to the doctor's own patient list endpoint (name/phone, case-insensitive partial match, still scoped to that doctor's own patients only).
- `apps/appointments/views.py` — appointment creation now fires an in-app `Notification` to whichever side (doctor and/or patient) didn't create it themselves.
- `apps/notifications/models.py` — added an `APPOINTMENT` notification type (migration `0004_alter_notification_notification_type` generated).
- Added 6 new backend tests covering the search param and the appointment-notification behavior (`apps/patients/tests/test_patients.py`, `apps/appointments/tests/test_appointments.py`).

**Frontend**
- `api/patients.api.js` — added `searchMyPatients(query)`, real server-side search.
- `pages/doctor/Patients.jsx` — rewritten to debounce and call the real search endpoint in live mode, with loading spinner and error banner; mock mode keeps its in-memory filter (no backend to hit there).
- `context/DataContext.jsx` — patients now live-fetch for the `PATIENT` role too (via `GET /patients/me/`), not just `DOCTOR`; removed the duplicate check-in POST; alerts now live-fetch for doctors.
- `api/checkin.api.js` — added `waitForCheckinResult`, which polls the checkin back out after submission until the backend's AI verdict lands, and maps it into the shape the UI expects.
- `api/ai.api.js` — now mock-mode-only (throws if called in live mode), since the live AI verdict doesn't come from a dedicated "analyze" endpoint.
- `api/medication.api.js` — `markMedicationStatus("TAKEN")` now actually acknowledges the patient's pending reminder log server-side.
- `api/alerts.api.js` — added `getAlerts()` (real fetch, normalizes severity/status casing); fixed `resolveAlert` to send `POST` instead of `PUT`.
- `api/appointment.api.js` — fully rewritten against real endpoints (`getMyAppointments`, `confirmAppointment`, `cancelAppointment`, `createAppointment`).
- `pages/patient/Appointments.jsx` (new) + route `/patient/appointments` — patients can now see their appointments and confirm/cancel them.
- `pages/doctor/PatientProfile.jsx` — "Schedule Follow-up" now creates a real `Appointment` via the API (with error handling and a saving state), in addition to the existing local echo.
- `pages/patient/Home.jsx` — "Next Follow-up" card now shows real upcoming appointment data in live mode; added a link to the new Appointments page.
- `components/layout/NotificationBell.jsx` (new) — real notification bell with unread badge, dropdown list, and mark-as-read; wired into the Doctor `Topbar`, `ReceptionistLayout`, and Patient `Home`.
- `Topbar.jsx` — the decorative, non-functional "Search patients…" box is now a real button that navigates to the doctor's (working) patient search page.
- `pages/patient/LabResults.jsx`, `pages/patient/CheckIn.jsx` — added explicit error states instead of silently falling back to an indistinguishable "empty" UI or hanging on "Analyzing…" forever.
- `src/api/reception.api.js` — emptied to a documented no-op stub (workspace files can't be deleted from this session; it exports nothing and points at the real module to use).
- `src/components/patient/AppointmentFollowUp.jsx` — annotated as not routed/not backed by any real endpoint (patients cannot self-book — only Doctor/Receptionist can create appointments, confirmed by existing backend permission tests); left in place, unrouted, as before.

## 3. Verified Features

- **Backend**: `python manage.py check` — clean. `makemigrations --check` — no drift. Full test suite: **220/220 passing** (214 pre-existing + 6 new), including the new search and notification tests.
- **AI Engine**: **315/315 tests passing**, untouched. Manually verified `/api/v1/health`, `/api/v1/analyze` (all 4 workflows: risk scoring, Low/Medium/High classification, trend detection, medication adherence, follow-up action, alert recipient), `/api/v1/lab-analysis`, `/api/v1/history/summary`, and 422 validation errors on bad payloads — all correct.
- **Frontend**: production build (`vite build`) succeeds cleanly with every change applied — 1693 modules, no errors (one pre-existing bundle-size warning, not an error).
- Confirmed by direct code trace (not by clicking through a live UI — see note below): doctor search now hits a real, permission-scoped backend endpoint; patient data now populates for the `PATIENT` role; check-in submission is a single POST plus a poll for the AI verdict; medication "taken" now calls the backend; appointments are created, listed, confirmed, and cancelled against the real `Appointment` model on both doctor and patient sides; notifications render real data for doctor/patient/receptionist.

**Important caveat**: this session's browser tooling cannot reach `localhost` servers started in this environment, so the fixes above were verified via the backend/AI-engine automated test suites, a clean production build, and careful code-path tracing — not by clicking through the running app end-to-end. Please do the manual click-through in section 7 before the demo.

## 4. Remaining Issues

- **No patient-facing "My Documents" page.** Documents are currently doctor-only in the routing — the backend supports patient access, but no page surfaces it. Not fixed (P1, time-boxed out).
- **`AppointmentFollowUp.jsx`** stays unrouted/unused — its premise (patient self-books an open time slot) has no backend support (no slots endpoint; patients are explicitly forbidden from creating appointments). Left as reference, clearly annotated.
- **Reception role currently never receives notifications** — no backend event targets a receptionist user yet, so their new notification bell will legitimately always read zero. Not a bug, just nothing routes to that role today.
- **Rotated JWT refresh tokens aren't blacklisted** (`BLACKLIST_AFTER_ROTATION=False`) — minor hardening gap, not exploitable without a token already being compromised.
- **No dedicated "unread count" notification endpoint** — the frontend derives it from `?unread=true` + pagination count, which works but costs an extra round trip.
- Two markdown docs in the repo root (`database/BACKEND_RECONCILIATION.md`) already flag that the raw `database/schema.sql` (used to init a fresh Postgres container) and Django's own migrations model overlapping-but-different schemas. This predates this session and wasn't touched — worth resolving before relying on `docker-compose up` from a clean volume.

## 5. Configuration Required

Nothing was hardcoded; everything below is environment-driven and already has placeholders in `backend/.env.example`.

- **SMTP**: currently on the console backend (emails print to logs, nothing is actually sent). To go live: set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, plus `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` in `backend/.env`.
- **AI Engine URL**: `backend/.env` already sets `AI_ENGINE_URL=http://localhost:8001` (matches the `dev:ai-engine` npm script's port) — no action needed for local dev; the AI Engine has no auth, so if this is ever deployed off localhost, put it behind a network boundary the Django backend alone can reach.
- **Django secret / JWT signing key**: use a real ≥32-byte `DJANGO_SECRET_KEY` outside of local dev (the test suite's short key triggers a `PyJWT` insecure-key-length warning by design, since tests aren't meant to be secure).

## 6. Exact Startup Commands

From the repo root:

```
npm run dev
```

This runs all three services together (`concurrently`): frontend on Vite's default port, backend on `0.0.0.0:8000`, AI Engine on port `8001`. Individually:

```
npm run dev:frontend      # Vite dev server
npm run dev:backend       # cd backend && ./venv/bin/python manage.py runserver 0.0.0.0:8000
npm run dev:ai-engine     # cd ai-engine && ./.venv/bin/python -m uvicorn app.main:app --reload --port 8001
```

Database / services (Postgres, etc.) via Docker:

```
docker-compose up
```

Backend virtualenv note: `backend/venv` in this repo is a broken symlink pointing at an Anaconda path from the original dev machine. If `./venv/bin/python` doesn't resolve on your machine, rebuild it:

```
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Same applies to `ai-engine/.venv` if needed:

```
cd ai-engine
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## 7. Demo Script

1. **Reception** logs in → Reception Dashboard. Register a new patient (assign to a doctor), confirm success feedback.
2. **Reception** searches for that patient by phone number → confirm it's found (this path was already working).
3. **Reception** books an appointment for that patient with their doctor.
4. **Doctor** logs in → Dashboard loads with real patient counts (no hardcoded stats).
5. **Doctor** goes to Patients → types into the search box → confirm real-time results come back from the backend (not just a client-side filter) — this was the flagged priority bug, now fixed.
6. **Doctor** opens the patient just registered → confirm profile, medications, labs, documents tabs load (empty is fine for a brand-new patient).
7. **Doctor** clicks the bell in the top bar → confirm the new appointment-booked notification appears (fired by step 3).
8. **Doctor** uses "Schedule Follow-up" on the patient → confirm it succeeds (this now creates a real `Appointment`, not just a local UI value).
9. **Patient** redeems their invitation / logs in → Home shows their real risk status and the "Next Follow-up" card matching what the doctor just scheduled.
10. **Patient** taps the bell → confirm the follow-up notification appears.
11. **Patient** goes to the new **Appointments** page (linked from Home) → confirm the appointment is listed, and confirms it.
12. **Patient** does a Daily Check-in → confirm the flow no longer hangs, shows a risk result, and only ever creates one check-in server-side (previously created two).
13. **Doctor** returns to Alerts → if the check-in was medium/high risk, confirm the alert appears and can be resolved (previously resolve was silently broken — 405 error).
