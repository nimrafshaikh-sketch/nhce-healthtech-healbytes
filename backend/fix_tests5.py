import glob

# 1. test_alerts.py (severity -> risk_level, recipient_role -> recipient_type)
f = 'apps/alerts/tests/test_alerts.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('severity="high"', 'risk_level="HIGH"')
c = c.replace('recipient_role="doctor_and_caretaker"', 'recipient_type="DOCTOR"')
with open(f, 'w') as fp: fp.write(c)

# 2. test_medications.py (frequency -> frequency_per_day)
f = 'apps/medications/tests/test_medications.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('frequency="once_daily"', 'frequency_per_day=1')
c = c.replace('"frequency": "once_daily"', '"frequency_per_day": 1')
c = c.replace('"name": "Aspirin"', '"medicine_name": "Aspirin"')
c = c.replace('MedicationReminderLog', 'MedicationAdherence')
with open(f, 'w') as fp: fp.write(c)

# 3. tasks.py (MedicationReminderLog -> MedicationAdherence)
f = 'apps/medications/tasks.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('MedicationReminderLog', 'MedicationAdherence')
with open(f, 'w') as fp: fp.write(c)

# 4. services.py (doctor.email -> doctor.user.email)
f = 'apps/notifications/services.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('doctor.email', 'doctor.user.email')
with open(f, 'w') as fp: fp.write(c)

# 5. test_patients.py (ensure date_of_birth is there)
f = 'apps/patients/tests/test_patients.py'
with open(f, 'r') as fp: c = fp.read()
# Replace payload one more time to be absolutely sure
c = c.replace('{"name": "New Patient"}', '{"name": "New Patient", "date_of_birth": "1990-01-01"}')
# And if it is still failing, it's possible it was missing entirely in post
c = c.replace('self.client.post(reverse("patient-list-create"), {"name": "New Patient"})', 'self.client.post(reverse("patient-list-create"), {"name": "New Patient", "date_of_birth": "1990-01-01"})')
with open(f, 'w') as fp: fp.write(c)
