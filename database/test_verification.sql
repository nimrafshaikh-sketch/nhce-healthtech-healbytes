-- ============================================================================
-- HealBytes — verification / smoke-test script
-- Not part of the schema. Safe to run repeatedly against a scratch database.
-- Exercises: inserts for every table, FK integrity, unique constraints,
-- check constraints, cascade behavior, and the AI-context retrieval query.
-- ============================================================================

\echo '--- 1. Insert doctor user + doctor profile ---'
INSERT INTO users (name, email, phone, password_hash, role)
VALUES ('Dr. Asha Rao', 'asha.rao@healbytes.test', '+91-9000000001', 'bcrypt$fakehash$doctor1', 'DOCTOR')
RETURNING id \gset doctor_user_

INSERT INTO doctors (user_id, specialization, hospital_name)
VALUES (:doctor_user_id, 'Cardiology', 'HealBytes General Hospital')
RETURNING id \gset doctor_

\echo '--- 2. Insert patient user + patient record (with caretaker + invitation code) ---'
INSERT INTO users (name, email, phone, password_hash, role)
VALUES ('Ramesh Kumar', 'ramesh.kumar@healbytes.test', '+91-9000000002', 'bcrypt$fakehash$patient1', 'PATIENT')
RETURNING id \gset patient_user_

INSERT INTO patients (user_id, doctor_id, name, date_of_birth, mobile_number, caretaker_name, caretaker_email, invitation_code, invitation_code_expires_at)
VALUES (:patient_user_id, :doctor_id, 'Ramesh Kumar', '1958-03-14', '+91-9000000002', 'Sunita Kumar', 'sunita.kumar@healbytes.test', 'INV-ABC123', now() + interval '7 days')
RETURNING id \gset patient_

\echo '--- 3. Insert medication + reminder + adherence ---'
INSERT INTO medications (patient_id, medicine_name, dosage, frequency_per_day, start_date, end_date, instructions)
VALUES (:patient_id, 'Metformin', '500mg', 2, CURRENT_DATE - 30, NULL, 'Take after meals')
RETURNING id \gset med_

INSERT INTO medication_reminders (medication_id, reminder_time, is_active)
VALUES (:med_id, '08:00', TRUE), (:med_id, '20:00', TRUE);

INSERT INTO medication_adherence (medication_id, patient_id, scheduled_time, taken_at, status)
VALUES
  (:med_id, :patient_id, now() - interval '12 hours', now() - interval '12 hours' + interval '10 minutes', 'TAKEN'),
  (:med_id, :patient_id, now() - interval '1 day', NULL, 'MISSED');

\echo '--- 4. Insert medical history (JSONB fields) ---'
INSERT INTO medical_history (patient_id, diagnosis, treatment, notes, recorded_by, symptoms, allergies, previous_relevant_records)
VALUES (
  :patient_id, 'Type 2 Diabetes', 'Metformin + lifestyle changes', 'Stable, monitor A1C quarterly',
  :doctor_user_id,
  '["fatigue", "increased thirst"]'::jsonb,
  '["penicillin"]'::jsonb,
  '[{"date": "2024-11-01", "note": "A1C 7.2%"}]'::jsonb
)
RETURNING id \gset hist_

\echo '--- 5. Insert daily check-in (AI fields NULL initially) ---'
INSERT INTO daily_checkins (patient_id, symptoms, severity_score, duration, notes, checkin_date)
VALUES (:patient_id, 'headache, dizziness', 6, '2 days', 'Started after skipping breakfast', CURRENT_DATE)
RETURNING id \gset checkin_

\echo '--- 6. Simulate AI engine writing back its result ---'
UPDATE daily_checkins
SET ai_risk_level = 'MEDIUM',
    ai_risk_score = 62,
    ai_reason = 'Elevated severity score combined with a recent missed dose',
    ai_recommended_action = 'Contact patient within 24h; confirm medication adherence'
WHERE id = :checkin_id;

\echo '--- 7. Generate alert from that check-in ---'
INSERT INTO alerts (patient_id, checkin_id, risk_level, recipient_type, title, message, risk_score, reason, follow_up_action)
VALUES (
  :patient_id, :checkin_id, 'MEDIUM', 'BOTH',
  'Elevated risk check-in for Ramesh Kumar',
  'Patient reported headache and dizziness with a recent missed Metformin dose.',
  62, 'Elevated severity score combined with a recent missed dose',
  'Contact patient within 24h; confirm medication adherence'
)
RETURNING id \gset alert_

\echo '--- 8. Insert QR access record (token stored as sha256 hash) ---'
INSERT INTO qr_access (patient_id, token, expires_at, accessed_by, access_status)
VALUES (:patient_id, encode(sha256('raw-demo-token-not-stored'::bytea), 'hex'), now() + interval '15 minutes', NULL, 'PENDING')
RETURNING id \gset qr_

\echo '=== ALL INSERTS SUCCEEDED ==='

\echo '--- CONSTRAINT TEST: duplicate email should fail ---'
DO $$
BEGIN
  BEGIN
    INSERT INTO users (name, email, password_hash, role) VALUES ('Dup', 'ASHA.RAO@healbytes.test', 'x', 'DOCTOR');
    RAISE EXCEPTION 'FAIL: duplicate email (case-insensitive) was allowed';
  EXCEPTION WHEN unique_violation THEN
    RAISE NOTICE 'PASS: case-insensitive unique email enforced';
  END;
END $$;

\echo '--- CONSTRAINT TEST: bad role should fail ---'
DO $$
BEGIN
  BEGIN
    INSERT INTO users (name, email, password_hash, role) VALUES ('Bad Role', 'bad.role@healbytes.test', 'x', 'CARETAKER');
    RAISE EXCEPTION 'FAIL: CARETAKER role was allowed';
  EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'PASS: role CHECK constraint rejects CARETAKER';
  END;
END $$;

\echo '--- CONSTRAINT TEST: end_date before start_date should fail ---'
DO $$
BEGIN
  BEGIN
    INSERT INTO medications (patient_id, medicine_name, dosage, frequency_per_day, start_date, end_date)
    VALUES (currval(pg_get_serial_sequence('patients','id')), 'Bad Med', '10mg', 1, CURRENT_DATE, CURRENT_DATE - 5);
    RAISE EXCEPTION 'FAIL: end_date before start_date was allowed';
  EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'PASS: end_date >= start_date CHECK enforced';
  END;
END $$;

\echo '--- CONSTRAINT TEST: bad adherence status should fail ---'
DO $$
BEGIN
  BEGIN
    INSERT INTO medication_adherence (medication_id, patient_id, scheduled_time, status)
    VALUES (currval(pg_get_serial_sequence('medications','id')), currval(pg_get_serial_sequence('patients','id')), now(), 'PENDING');
    RAISE EXCEPTION 'FAIL: invalid adherence status was allowed';
  EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'PASS: adherence status CHECK enforced';
  END;
END $$;

\echo '--- CONSTRAINT TEST: orphan FK should fail ---'
DO $$
BEGIN
  BEGIN
    INSERT INTO medications (patient_id, medicine_name, dosage, frequency_per_day, start_date)
    VALUES (999999, 'Ghost Med', '1mg', 1, CURRENT_DATE);
    RAISE EXCEPTION 'FAIL: FK to nonexistent patient was allowed';
  EXCEPTION WHEN foreign_key_violation THEN
    RAISE NOTICE 'PASS: medications.patient_id FK enforced';
  END;
END $$;

\echo '--- CASCADE TEST: deleting a medication cascades to reminders + adherence ---'
DO $$
DECLARE
  test_patient_id BIGINT;
  test_med_id BIGINT;
  reminder_count INT;
  adherence_count INT;
BEGIN
  test_patient_id := currval(pg_get_serial_sequence('patients','id'));
  INSERT INTO medications (patient_id, medicine_name, dosage, frequency_per_day, start_date)
  VALUES (test_patient_id, 'Temp Med', '1mg', 1, CURRENT_DATE) RETURNING id INTO test_med_id;
  INSERT INTO medication_reminders (medication_id, reminder_time) VALUES (test_med_id, '09:00');
  INSERT INTO medication_adherence (medication_id, patient_id, scheduled_time, status) VALUES (test_med_id, test_patient_id, now(), 'TAKEN');

  DELETE FROM medications WHERE id = test_med_id;

  SELECT count(*) INTO reminder_count FROM medication_reminders WHERE medication_id = test_med_id;
  SELECT count(*) INTO adherence_count FROM medication_adherence WHERE medication_id = test_med_id;

  IF reminder_count = 0 AND adherence_count = 0 THEN
    RAISE NOTICE 'PASS: deleting medication cascaded to reminders (%) and adherence (%)', reminder_count, adherence_count;
  ELSE
    RAISE EXCEPTION 'FAIL: cascade delete from medications did not clean up children';
  END IF;
END $$;

\echo '--- RESTRICT TEST: deleting a doctor with patients should fail ---'
DO $$
BEGIN
  BEGIN
    DELETE FROM doctors WHERE id = currval(pg_get_serial_sequence('doctors','id'));
    RAISE EXCEPTION 'FAIL: doctor with existing patients was deleted';
  EXCEPTION WHEN foreign_key_violation THEN
    RAISE NOTICE 'PASS: doctors.id ON DELETE RESTRICT protected doctor with patients';
  END;
END $$;

\echo '=== ALL CONSTRAINT/CASCADE TESTS PASSED ==='

\echo '--- RELATIONSHIP VERIFICATION: full patient tree join ---'
SELECT
  p.id AS patient_id, p.name AS patient_name, d.hospital_name, u.email AS doctor_email,
  (SELECT count(*) FROM medications m WHERE m.patient_id = p.id) AS medication_count,
  (SELECT count(*) FROM daily_checkins c WHERE c.patient_id = p.id) AS checkin_count,
  (SELECT count(*) FROM alerts a WHERE a.patient_id = p.id) AS alert_count,
  (SELECT count(*) FROM medical_history h WHERE h.patient_id = p.id) AS history_count,
  (SELECT count(*) FROM qr_access q WHERE q.patient_id = p.id) AS qr_count
FROM patients p
JOIN doctors d ON d.id = p.doctor_id
JOIN users u ON u.id = d.user_id
WHERE p.id = :patient_id;

\echo '--- AI-CONTEXT QUERY: everything the AI engine needs for one risk analysis, in one round trip ---'
SELECT jsonb_build_object(
  'patient', (
    SELECT jsonb_build_object(
      'id', p.id, 'name', p.name, 'date_of_birth', p.date_of_birth,
      'caretaker_name', p.caretaker_name, 'caretaker_email', p.caretaker_email
    ) FROM patients p WHERE p.id = :patient_id
  ),
  'current_checkin', (
    SELECT to_jsonb(c) FROM daily_checkins c WHERE c.id = :checkin_id
  ),
  'previous_checkins', (
    SELECT coalesce(jsonb_agg(to_jsonb(c)), '[]'::jsonb)
    FROM (
      SELECT * FROM daily_checkins
      WHERE patient_id = :patient_id AND id != :checkin_id
      ORDER BY checkin_date DESC LIMIT 10
    ) c
  ),
  'medical_history', (
    SELECT coalesce(jsonb_agg(to_jsonb(h) ORDER BY h.recorded_at DESC), '[]'::jsonb)
    FROM medical_history h WHERE h.patient_id = :patient_id
  ),
  'medications', (
    SELECT coalesce(jsonb_agg(to_jsonb(m)), '[]'::jsonb)
    FROM medications m WHERE m.patient_id = :patient_id AND (m.end_date IS NULL OR m.end_date >= CURRENT_DATE)
  ),
  'medication_adherence_last_30d', (
    SELECT coalesce(jsonb_agg(to_jsonb(ma) ORDER BY ma.scheduled_time DESC), '[]'::jsonb)
    FROM medication_adherence ma
    WHERE ma.patient_id = :patient_id AND ma.scheduled_time >= now() - interval '30 days'
  )
) AS ai_context;

\echo '=== VERIFICATION SCRIPT COMPLETE ==='
