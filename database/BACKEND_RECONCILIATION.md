# Backend ↔ Database Reconciliation Spec

For Member 2 (Backend). Purpose: make the Django models on `feature/backend` match the approved schema in `database/schema.sql`, which is finalized and not being changed. This document is the full diff — table by table, field by field — plus the two decisions that need a team call before code changes, and the immediate bug that's separate from all of this.

## 0. The bug you're actually seeing right now (not a schema issue)

The invitation-code screen fails because the frontend is running in mock mode. `src/api/client.js`: `USE_MOCK` is `true` unless `VITE_USE_MOCK_DATA=false` is set. `invitation.api.js`'s `verifyInvitation`/`generateInvitation` never call the Django API while mocked — they search an in-memory `patients` array in the browser's `DataContext`. Doctor and patient are separate sessions/devices, so the patient's browser never has the code the doctor's browser generated. The "HB-XXXXXX" format is mock/demo copy only — real Django-generated codes are plain 8-char alphanumeric with no prefix (see `apps/invitations/models.py: generate_invitation_code`). Fix: set `VITE_USE_MOCK_DATA=false` and point `VITE_API_BASE_URL` at the running Django server once the reconciliation below is done (no point wiring it up against a schema that's about to change).

## 1. Two architectural decisions needed before anyone writes code

These aren't naming fixes — changing them touches multiple apps and existing migrations. Flagging rather than deciding for you.

**A. `doctors` as its own table.** Approved schema has `doctors` (id, user_id, specialization, hospital_name) separate from `users`. Django currently has no `doctors` table at all — `specialization`/`license_number` live directly on `accounts.User`, and every other app (`patients`, `medications`, `alerts`) FKs straight to `settings.AUTH_USER_MODEL` with `limit_choices_to={"role": "doctor"}`. Matching the approved schema means: create `apps/doctors` with a `Doctor` model (`user` OneToOne, `specialization`, `hospital_name`), migrate `specialization`/`license_number` off `User` (note: `hospital_name` doesn't exist on `User` today — new data), and repoint `Patient.doctor`, `Medication.prescribed_by`, `InvitationCode.doctor` from `User` to `Doctor`. That's a real, multi-app migration, not a rename.

**B. QR access model.** Approved schema is a stateful `qr_access` table: a token (hashed) with `expires_at`/`used_at`/`is_active`/`access_status` rows. Django's current design is a stateless signed JWT (never persisted) plus `qr.QRScanLog`, an audit-only table of scan attempts. These are two different security models, not a field mismatch — stateful tokens support revocation and a real "PENDING/GRANTED/DENIED" lifecycle; stateless JWTs don't need a lookup table at all but can't be revoked before expiry. Confirm with the team which one you actually want before touching `apps/qr`.

## 2. Table-by-table field diff

### users ↔ `accounts.User`
| Approved | Django | Note |
|---|---|---|
| `role` CHECK `DOCTOR`/`PATIENT` | `role` choices `doctor`/`patient` | casing differs — harmless if the API normalizes, but pick one casing convention repo-wide |
| — | `phone_number`, `specialization`, `license_number` on `User` | `specialization`/`license_number` should move to the new `doctors` table (see 1A); `phone_number` maps to approved `users.phone` |
| `is_active` | inherited from `AbstractUser` | ✅ already present |

### doctors ↔ *(no table)*
Needs to be created — see 1A. Approved fields: `id, user_id, specialization, hospital_name, created_at, updated_at`.

### patients ↔ `patients.Patient`
| Approved | Django | Note |
|---|---|---|
| `name` | `full_name` | rename |
| `mobile_number` | `phone_number` | rename |
| `doctor_id → doctors.id` | `doctor → User` | repoint once `doctors` exists (1A) |
| `invitation_code`, `invitation_code_expires_at` | *(lives in separate `invitations.InvitationCode`)* | approved schema keeps these inline on `patients`; Django's separate-table design is arguably cleaner but diverges — decide whether to fold `InvitationCode` into `patients` columns or keep it separate and treat that divergence as accepted (flag to team) |
| — | `gender`, `address`, `medical_notes`, `caretaker_relationship`, `caretaker_phone_number`, `is_active` | not in approved schema — either drop, or treat as intentional backend-only extensions or park until a future patients-table change is requested |
| `caretaker_name`, `caretaker_email` | same names | ✅ match |
| `date_of_birth` | same | ✅ match |

### medications ↔ `medications.Medication`
| Approved | Django | Note |
|---|---|---|
| `medicine_name` | `name` | rename |
| `frequency_per_day` INTEGER | `frequency` enum (`once_daily`/`twice_daily`/...) | approved schema expects a count, not a fixed enum — needs a real type change, not just a rename |
| — | `reminder_times` JSON list on `Medication` | duplicates what `medication_reminders` table should own — see below |
| — | `prescribed_by`, `reminders_enabled`, `is_active` | not in approved schema |
| `dosage`, `instructions`, `start_date`, `end_date` | same | ✅ match |

### medication_reminders ↔ *(folded into `Medication.reminder_times`)*
Approved schema wants a real table (`id, medication_id, reminder_time, is_active`), one row per reminder. Django currently stores reminder times as a JSON array on the medication itself. To match, extract `reminder_times` into its own model. (`medications.MedicationReminderLog` is a different thing — a dispatch audit log — and isn't in conflict; it can stay as an extra table.)

### medication_adherence ↔ *(does not exist)*
No model anywhere tracks a scheduled dose's TAKEN/MISSED/SKIPPED status. This is a genuine gap — needs a new model: `medication_id, patient_id, scheduled_time, taken_at, status`.

### daily_checkins ↔ `checkins.DailyCheckin`
| Approved | Django | Note |
|---|---|---|
| `symptoms` (text) | `symptoms` JSON list | Django's is arguably better for AI consumption — decide whether to update the approved column type to JSONB to match, or have Django serialize to text |
| `severity_score` | *(not present — has `pain_level` 0-10 instead)* | different concept/name; map or rename |
| `duration` | *(not present)* | missing |
| — | `mood`, `vitals` | not in approved schema |
| `ai_reason` | `ai_notes` | rename |
| `ai_risk_level` (open text) | `ai_risk_level` enum `pending/low/medium/high/unavailable` | Django already defines a concrete scale here — worth reusing to finally close the open "no risk scale defined" item from `database/README.md`, if AI/Backend agree |
| `ai_risk_score` (open numeric) | `ai_risk_score` float 0.0–1.0 | same — Django already picked a scale (0–1 float); confirm with Member 4 and adopt it schema-wide |
| — | `ai_processed_at` | not approved, but genuinely useful — answers the open item about no timestamp for when AI finished. Worth requesting as an approved addition rather than dropping it. |
| — | `ai_notification_recipient` | not in approved schema |
| — | `UniqueConstraint(patient, checkin_date)` — one check-in/day | approved schema has no such constraint; confirm this is the intended product behavior (only one check-in allowed per calendar day) before relying on it |

### alerts ↔ `alerts.Alert`
| Approved | Django | Note |
|---|---|---|
| `risk_level` | `severity` | rename |
| `recipient_type` (`DOCTOR`/`CARETAKER`/`BOTH`) | `recipient_role` (`doctor`/`caretaker`/`doctor_and_caretaker`) | rename + value rename (`BOTH` → `doctor_and_caretaker`) |
| `status` (`UNREAD`/`READ`/`RESOLVED`) | `status` (`open`/`acknowledged`/`resolved`) | different value set — needs a mapping decision, not just casing |
| `title`, `message`, `risk_score`, `follow_up_action` | *(none of these exist)* | all four approved fields are missing from Django's `Alert` model — this is the biggest gap in this table |
| — | `acknowledged_by`, `acknowledged_at`, `email_sent`, `email_sent_at`, `email_error` | not approved — decide keep-as-extension vs drop |
| `reason` | `reason` | ✅ match |

### medical_history ↔ *(does not exist)*
No app/model anywhere. This is a full gap — needs a new Django app with the approved fields: `id, patient_id, diagnosis, treatment, notes, recorded_by, recorded_at, symptoms, allergies, previous_relevant_records, updated_at`.

### qr_access ↔ `qr.QRScanLog` (+ stateless JWT)
See decision 1B above — this isn't a field-level diff, it's a different mechanism. `QRScanLog` (patient, scanned_by, success, failure_reason) is an audit trail, not the approved stateful token table.

## 3. Extra Django tables with no approved-schema counterpart
Not necessarily wrong — flagging so the team decides keep/drop/defer rather than these silently diverging further:
- `invitations.InvitationCode` (see 2, patients)
- `notifications.Notification`, `notifications.EmailNotificationLog`
- `medications.MedicationReminderLog`
- `qr.QRScanLog` (if the team keeps a stateful `qr_access` table per 1B, this could become redundant or stay as a pure audit log alongside it)

## 4. Migration mechanics note
Every app already has a `migrations/0001_initial.py`. If any of these have been run against a real dev database, don't hand-edit `0001_initial.py` — write new migrations (`makemigrations` after the model changes) so existing data/history isn't clobbered. If nothing's been migrated against a real Postgres yet (likely, given the mock-mode finding above), squashing back into clean initial migrations is safe and probably cleaner.
