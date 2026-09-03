-- ============================================================================
-- HealBytes — PostgreSQL Schema
-- AI-Based Autonomous Healthcare Coordination & Follow-up Agent
--
-- Database: healbytes
-- Owner/app role: healbytes_app
-- Author: Member 3 (Database)
--
-- This file is idempotent (safe to re-run): every object uses
-- IF NOT EXISTS / OR REPLACE guards. Apply with:
--   psql "$DATABASE_URL" -f database/schema.sql
--
-- Design notes (see database/README.md for full rationale):
--  - IDs use PostgreSQL identity columns (BIGINT GENERATED ALWAYS AS IDENTITY).
--  - All timestamps use TIMESTAMPTZ (stored in UTC, converted at the edges).
--  - Enum-like fields (role, status, recipient_type, etc.) use TEXT + CHECK
--    constraints instead of native ENUM types, so new values can be added
--    later with a simple constraint swap instead of ALTER TYPE.
--  - No risk-score "scale" (e.g. 0-100 vs 1-10) is enforced by CHECK
--    constraints for severity_score / ai_risk_score / risk_score, because
--    no existing backend/AI code defines that scale yet. NOT NULL / nullability
--    is enforced; numeric bounds should be added once Member 4 (AI) confirms
--    the scale.
--  - This project has no existing backend/ORM code at the time this schema
--    was written (verified by inspecting the repo — see report). Plain SQL
--    was used so any ORM (Prisma, Sequelize, SQLAlchemy, raw pg/psycopg2)
--    can point at it later without re-architecting.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- Shared trigger: keep updated_at current on UPDATE
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 1. users
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           TEXT        NOT NULL,
    email          TEXT        NOT NULL,
    phone          TEXT,
    password_hash  TEXT        NOT NULL,
    role           TEXT        NOT NULL CHECK (role IN ('DOCTOR', 'PATIENT')),
    is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Case-insensitive uniqueness: Email@x.com and email@x.com are the same login.
CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_lower ON users (lower(email));
CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- 2. doctors  (users 1 -> 1 doctors)
-- ============================================================================
CREATE TABLE IF NOT EXISTS doctors (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT      NOT NULL UNIQUE
                        REFERENCES users(id) ON DELETE RESTRICT,
    specialization  TEXT,
    hospital_name   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_doctors_user_id ON doctors (user_id);

DROP TRIGGER IF EXISTS trg_doctors_updated_at ON doctors;
CREATE TRIGGER trg_doctors_updated_at
    BEFORE UPDATE ON doctors
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- 3. patients  (users -> patients, doctors -> patients)
-- ----------------------------------------------------------------------------
-- user_id is nullable: a doctor can create a patient record (with caretaker
-- name/email + invitation_code) before the patient/caretaker has signed up
-- for a login. It is linked once they redeem the invitation code.
-- ============================================================================
CREATE TABLE IF NOT EXISTS patients (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id                     BIGINT UNIQUE
                                    REFERENCES users(id) ON DELETE SET NULL,
    doctor_id                   BIGINT NOT NULL
                                    REFERENCES doctors(id) ON DELETE RESTRICT,
    name                        TEXT        NOT NULL,
    date_of_birth               DATE        NOT NULL,
    mobile_number               TEXT,
    caretaker_name              TEXT,
    caretaker_email             TEXT,
    invitation_code             TEXT UNIQUE,
    invitation_code_expires_at  TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_patients_doctor_id ON patients (doctor_id);
CREATE INDEX IF NOT EXISTS ix_patients_user_id ON patients (user_id);

DROP TRIGGER IF EXISTS trg_patients_updated_at ON patients;
CREATE TRIGGER trg_patients_updated_at
    BEFORE UPDATE ON patients
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- 4. medications  (patients 1 -> many medications)
-- ============================================================================
CREATE TABLE IF NOT EXISTS medications (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_id         BIGINT      NOT NULL
                            REFERENCES patients(id) ON DELETE CASCADE,
    medicine_name      TEXT        NOT NULL,
    dosage             TEXT        NOT NULL,
    frequency_per_day  INTEGER     NOT NULL CHECK (frequency_per_day > 0),
    start_date         DATE        NOT NULL,
    end_date           DATE,
    instructions       TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_medications_end_after_start
        CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS ix_medications_patient_id ON medications (patient_id);

DROP TRIGGER IF EXISTS trg_medications_updated_at ON medications;
CREATE TRIGGER trg_medications_updated_at
    BEFORE UPDATE ON medications
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- 5. medication_reminders  (medications 1 -> many medication_reminders)
-- ============================================================================
CREATE TABLE IF NOT EXISTS medication_reminders (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    medication_id  BIGINT      NOT NULL
                        REFERENCES medications(id) ON DELETE CASCADE,
    reminder_time  TIME        NOT NULL,
    is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_medication_reminders_medication_id
    ON medication_reminders (medication_id);

DROP TRIGGER IF EXISTS trg_medication_reminders_updated_at ON medication_reminders;
CREATE TRIGGER trg_medication_reminders_updated_at
    BEFORE UPDATE ON medication_reminders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- 6. medication_adherence
-- ----------------------------------------------------------------------------
-- No updated_at (not in approved field list). One row per scheduled dose;
-- UNIQUE(medication_id, scheduled_time) prevents duplicate adherence rows
-- for the same scheduled dose.
-- ============================================================================
CREATE TABLE IF NOT EXISTS medication_adherence (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    medication_id  BIGINT      NOT NULL
                        REFERENCES medications(id) ON DELETE CASCADE,
    patient_id     BIGINT      NOT NULL
                        REFERENCES patients(id) ON DELETE CASCADE,
    scheduled_time TIMESTAMPTZ NOT NULL,
    taken_at       TIMESTAMPTZ,
    status         TEXT        NOT NULL CHECK (status IN ('TAKEN', 'MISSED', 'SKIPPED')),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ux_medication_adherence_schedule
        UNIQUE (medication_id, scheduled_time)
);

CREATE INDEX IF NOT EXISTS ix_medication_adherence_patient_id
    ON medication_adherence (patient_id);
CREATE INDEX IF NOT EXISTS ix_medication_adherence_patient_scheduled
    ON medication_adherence (patient_id, scheduled_time DESC);

-- ============================================================================
-- 7. daily_checkins  (patients -> daily_checkins)
-- ----------------------------------------------------------------------------
-- AI result fields (ai_risk_level, ai_risk_score, ai_reason,
-- ai_recommended_action) are nullable and filled in by a later UPDATE once
-- the AI engine has processed the check-in. No updated_at column (not in
-- approved field list) — see report for the tracking implication.
-- ============================================================================
CREATE TABLE IF NOT EXISTS daily_checkins (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_id              BIGINT      NOT NULL
                                REFERENCES patients(id) ON DELETE CASCADE,
    symptoms                TEXT,
    severity_score          INTEGER,
    duration                TEXT,
    notes                   TEXT,
    checkin_date            DATE        NOT NULL DEFAULT CURRENT_DATE,
    ai_risk_level           TEXT,
    ai_risk_score           NUMERIC,
    ai_reason               TEXT,
    ai_recommended_action   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_daily_checkins_patient_date
    ON daily_checkins (patient_id, checkin_date DESC);

-- ============================================================================
-- 8. alerts
-- ----------------------------------------------------------------------------
-- checkin_id is nullable with ON DELETE SET NULL: if the source check-in is
-- ever removed, the alert (and its audit trail) is preserved.
-- ============================================================================
CREATE TABLE IF NOT EXISTS alerts (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_id        BIGINT      NOT NULL
                            REFERENCES patients(id) ON DELETE CASCADE,
    checkin_id        BIGINT
                            REFERENCES daily_checkins(id) ON DELETE SET NULL,
    risk_level        TEXT        NOT NULL,
    recipient_type    TEXT        NOT NULL CHECK (recipient_type IN ('DOCTOR', 'CARETAKER', 'BOTH')),
    title             TEXT        NOT NULL,
    message            TEXT        NOT NULL,
    status            TEXT        NOT NULL DEFAULT 'UNREAD'
                            CHECK (status IN ('UNREAD', 'READ', 'RESOLVED')),
    risk_score        NUMERIC,
    reason            TEXT,
    follow_up_action  TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_alerts_patient_id ON alerts (patient_id);
CREATE INDEX IF NOT EXISTS ix_alerts_checkin_id ON alerts (checkin_id);
CREATE INDEX IF NOT EXISTS ix_alerts_status ON alerts (status);

-- ============================================================================
-- 9. medical_history
-- ----------------------------------------------------------------------------
-- symptoms / allergies / previous_relevant_records use JSONB: no existing
-- backend defines their shape, and JSONB gives the AI engine flexible,
-- queryable historical context without a rigid column structure.
-- Suggested shapes (confirm with Member 2/4):
--   symptoms: ["fever", "cough"]
--   allergies: ["penicillin"]
--   previous_relevant_records: [{"date": "2025-01-01", "note": "..."}]
-- ============================================================================
CREATE TABLE IF NOT EXISTS medical_history (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_id                  BIGINT      NOT NULL
                                    REFERENCES patients(id) ON DELETE CASCADE,
    diagnosis                   TEXT,
    treatment                   TEXT,
    notes                       TEXT,
    recorded_by                 BIGINT
                                    REFERENCES users(id) ON DELETE SET NULL,
    recorded_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    symptoms                    JSONB,
    allergies                   JSONB,
    previous_relevant_records   JSONB,
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_medical_history_patient_id ON medical_history (patient_id);
CREATE INDEX IF NOT EXISTS ix_medical_history_recorded_at ON medical_history (patient_id, recorded_at DESC);

DROP TRIGGER IF EXISTS trg_medical_history_updated_at ON medical_history;
CREATE TRIGGER trg_medical_history_updated_at
    BEFORE UPDATE ON medical_history
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- 10. qr_access
-- ----------------------------------------------------------------------------
-- SECURITY: `token` stores a SHA-256 hash of the actual QR token, never the
-- raw value — same pattern as users.password_hash. The raw token is
-- generated by the backend, shown/embedded in the QR code once, and never
-- persisted. On scan, the backend hashes the presented token and looks up
-- this row by the hash. This means a database leak alone cannot be used to
-- forge QR access.
-- accessed_by is free text (not an FK to users): QR access exists precisely
-- for people without an account in the system (e.g. an ER clinician scanning
-- in an emergency), so it stores whatever identifier the backend captures
-- (name, badge ID, etc.).
-- ============================================================================
CREATE TABLE IF NOT EXISTS qr_access (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_id     BIGINT      NOT NULL
                        REFERENCES patients(id) ON DELETE CASCADE,
    token          TEXT        NOT NULL UNIQUE,
    expires_at     TIMESTAMPTZ NOT NULL,
    used_at        TIMESTAMPTZ,
    is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    accessed_by    TEXT,
    access_status  TEXT        NOT NULL DEFAULT 'PENDING'
                        CHECK (access_status IN ('PENDING', 'GRANTED', 'DENIED', 'EXPIRED', 'REVOKED'))
);

CREATE INDEX IF NOT EXISTS ix_qr_access_patient_id ON qr_access (patient_id);
CREATE INDEX IF NOT EXISTS ix_qr_access_expires_at ON qr_access (expires_at);

COMMIT;
