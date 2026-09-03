# HealBytes Database

PostgreSQL schema for HealBytes (AI-Based Autonomous Healthcare Coordination & Follow-up Agent). Owned by Member 3 (Database).

## Status

The repository had no backend code, ORM, or migrations when this was built (empty `database/schema.sql` was the only file). This schema is plain SQL — not tied to any ORM — so whichever backend stack Member 2 uses (Prisma, Sequelize, SQLAlchemy, raw `pg`/`psycopg2`, etc.) can point at it.

## Setup

1. Create the role and database (once, as a Postgres superuser):

```sql
CREATE ROLE healbytes_app WITH LOGIN PASSWORD 'choose-a-real-password';
CREATE DATABASE healbytes OWNER healbytes_app;
```

2. Copy `env.example` to `.env` and fill in the real password. The backend reads `DATABASE_URL`; never commit `.env` or hardcode the password in source.

3. Apply the schema (idempotent — safe to re-run):

```bash
psql "$DATABASE_URL" -f database/schema.sql
```

4. Optional: run the smoke test (inserts a doctor, patient, medication, reminder, adherence rows, check-in, alert, medical history, QR access; verifies constraints, cascades, and the AI-context query; cleans up after itself since it targets throwaway rows):

```bash
psql "$DATABASE_URL" -f database/test_verification.sql
```

## Tables (10, as approved)

`users → doctors → patients → { medications → { medication_reminders, medication_adherence }, daily_checkins → alerts, medical_history, qr_access }`

See `schema.sql` for the full DDL and inline rationale comments. Highlights:

- IDs: `BIGINT GENERATED ALWAYS AS IDENTITY` on every table.
- Timestamps: `TIMESTAMPTZ` everywhere (store/compare in UTC).
- `users.role` is restricted to `DOCTOR` / `PATIENT` only — **caretaker is a contact, not a login role** (confirmed with Backend, see Caretaker model below). Caretaker info lives on `patients.caretaker_name` / `caretaker_email`; caretakers can still receive alerts via `alerts.recipient_type`.
- Enum-like fields (`role`, `medication_adherence.status`, `alerts.recipient_type`/`status`, `qr_access.access_status`) use `TEXT` + `CHECK` rather than native `ENUM` types, so new values can be added later with a constraint swap instead of `ALTER TYPE`.
- `severity_score`, `ai_risk_score`, `ai_risk_level`, `alerts.risk_level`, `alerts.risk_score` have **no numeric/value range enforced** — no existing backend or AI code defines that scale yet. Add a `CHECK` once Member 4 confirms it (e.g. 0–100, or LOW/MEDIUM/HIGH/CRITICAL).
- `medical_history.symptoms` / `allergies` / `previous_relevant_records` are `JSONB` (no existing backend format to conflict with; flexible for AI context). Suggested shapes are in `schema.sql`.
- `qr_access.token` stores a **SHA-256 hash** of the token, never the raw value — same pattern as `password_hash`. See Security below.

## Cascade / delete behavior

| Deleting a... | Behavior |
|---|---|
| `patient` | Cascades: medications, medication_reminders/adherence (via medications), daily_checkins, alerts, medical_history, qr_access all removed |
| `medication` | Cascades: its reminders and adherence rows removed |
| `daily_checkin` | Its `alerts.checkin_id` is set NULL (alert record survives for audit) |
| `doctor` | **Restricted** — must reassign or remove their patients first |
| `user` (doctor role) | **Restricted** — must remove the doctor profile first |
| `user` (patient role) | `patients.user_id` set NULL — patient's medical record is preserved, just unlinked from a login |
| `user` (recorded medical_history) | `medical_history.recorded_by` set NULL — history entry preserved |

Rationale: patient-owned operational data cascades cleanly with the patient; anything that would silently destroy clinical history behind a user/doctor account deletion is blocked or preserved instead (soft-delete via `users.is_active` is the intended way to deactivate an account).

## Security

- No plaintext passwords or secrets anywhere in this schema or the repo. `password_hash` stores only what the backend's auth hashing (bcrypt/argon2, etc.) produces.
- `DATABASE_URL` / connection credentials come from environment variables (`env.example`), never hardcoded.
- QR tokens: the backend generates the raw token, embeds it in the QR code, and stores only its SHA-256 hash in `qr_access.token`. On scan, the backend hashes the presented token and looks up the row — a database leak alone cannot be replayed as a valid QR token.
- Authorization (who's allowed to see which patient's data) is application logic, not enforced in Postgres, per the spec.

## AI-context query (Member 4)

The AI engine needs: patient info + current check-in + previous check-ins + medical history + medication info + adherence — all without an extra table. `database/test_verification.sql` (bottom section) contains a single query that returns exactly this as one JSON object:

```sql
SELECT jsonb_build_object(
  'patient', (SELECT jsonb_build_object('id', p.id, 'name', p.name, 'date_of_birth', p.date_of_birth,
              'caretaker_name', p.caretaker_name, 'caretaker_email', p.caretaker_email)
              FROM patients p WHERE p.id = $1),
  'current_checkin', (SELECT to_jsonb(c) FROM daily_checkins c WHERE c.id = $2),
  'previous_checkins', (SELECT coalesce(jsonb_agg(to_jsonb(c)), '[]'::jsonb) FROM (
        SELECT * FROM daily_checkins WHERE patient_id = $1 AND id != $2
        ORDER BY checkin_date DESC LIMIT 10) c),
  'medical_history', (SELECT coalesce(jsonb_agg(to_jsonb(h) ORDER BY h.recorded_at DESC), '[]'::jsonb)
        FROM medical_history h WHERE h.patient_id = $1),
  'medications', (SELECT coalesce(jsonb_agg(to_jsonb(m)), '[]'::jsonb) FROM medications m
        WHERE m.patient_id = $1 AND (m.end_date IS NULL OR m.end_date >= CURRENT_DATE)),
  'medication_adherence_last_30d', (SELECT coalesce(jsonb_agg(to_jsonb(ma) ORDER BY ma.scheduled_time DESC), '[]'::jsonb)
        FROM medication_adherence ma WHERE ma.patient_id = $1 AND ma.scheduled_time >= now() - interval '30 days')
) AS ai_context;
-- params: $1 = patient_id, $2 = current checkin_id
```

Run it after inserting a new `daily_checkins` row (with AI fields still NULL), hand the JSON to the AI engine, then `UPDATE daily_checkins SET ai_risk_level=..., ai_risk_score=..., ai_reason=..., ai_recommended_action=... WHERE id=$2`, and insert into `alerts` if warranted.

## Backend integration (Member 2)

- Connect via `DATABASE_URL` (see `env.example`).
- Every field name in `schema.sql` matches the approved spec exactly (snake_case) — no renames.
- `users.role` accepts only `'DOCTOR'` / `'PATIENT'` (uppercase, enforced by CHECK). Caretakers never log in — see Caretaker model below.
- `patients.user_id` is nullable — a patient row can exist (created by a doctor, with `invitation_code`) before the patient/caretaker has an account. Link it on signup.
- Insert order respects FKs: `users` → `doctors`/`patients` → `medications` → `medication_reminders`/`medication_adherence`; `daily_checkins` → `alerts`.
- `daily_checkins` AI fields (`ai_risk_level`, `ai_risk_score`, `ai_reason`, `ai_recommended_action`) are NULL on insert; update them after the AI call returns.
- `qr_access.token`: send the raw token to the client/QR code, store only `sha256(token)` here.

## Caretaker model (confirmed with Backend)

Caretaker is a **contact on the patient record only** — not an account, not a role, not a table:

- No `caretakers` table, no `caretaker_id` anywhere.
- No caretaker user account and no caretaker login/authentication.
- No `CARETAKER` value in `users.role` (CHECK constraint stays `DOCTOR`/`PATIENT` only).
- Caretaker identity lives entirely in `patients.caretaker_name` and `patients.caretaker_email`.
- Caretakers still receive alerts: `alerts.recipient_type` supports `DOCTOR`, `CARETAKER`, `BOTH` — the backend resolves `CARETAKER`/`BOTH` recipients by reading `patients.caretaker_email` for that alert's patient, not by joining to a user account.

This was implemented this way from the first version of the schema and required no changes once confirmed.

## Conflicts / open items

1. **Risk-score scale.** `severity_score`, `ai_risk_score`, `alerts.risk_score`, and the `*risk_level` text fields have no enforced range/values yet, per the instruction not to invent a scale. Confirm the scale with Member 4 and I'll add the CHECK constraints.
2. **`daily_checkins` has no `updated_at`** (not in the approved field list), even though AI fields are written via a later UPDATE. This means there's no DB-level timestamp for "when did the AI finish processing this check-in." Flagging in case that's needed — I did not add it without approval.
3. **`medical_history.symptoms`/`allergies`/`previous_relevant_records` as JSONB** — no existing backend defined a format, so JSONB was used as the spec allows. Confirm the exact shape your API will send.
4. **`medication_reminders.reminder_time` is `TIME`** (time-of-day, e.g. `08:00`), not `TIMESTAMPTZ` — assumed since reminders recur daily. Flag if the backend expects a specific one-off timestamp instead.
