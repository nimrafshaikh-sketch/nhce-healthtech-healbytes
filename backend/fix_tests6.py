import glob

# Fix AlertSerializer
f = 'apps/alerts/serializers.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('"severity"', '"risk_level"')
with open(f, 'w') as fp: fp.write(c)

# Fix services.py
f = 'apps/notifications/services.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('get_severity_display', 'get_risk_level_display')
c = c.replace('patient.full_name', 'patient.name')
with open(f, 'w') as fp: fp.write(c)

# Fix test_medications.py
f = 'apps/medications/tests/test_medications.py'
with open(f, 'r') as fp: c = fp.read()
# missing fields in payload
c = c.replace('"name": "Aspirin"', '"medicine_name": "Aspirin"')
c = c.replace('"frequency": "once_daily"', '"frequency_per_day": 1')
c = c.replace('{"name": "Aspirin", "frequency": "once_daily", "dosage": "75mg", "start_date": "2026-01-01"}', '{"medicine_name": "Aspirin", "frequency_per_day": 1, "dosage": "75mg", "start_date": "2026-01-01"}')
# MedicationReminderTaskTests using doctor=doctor instead of doctor_profile
c = c.replace('doctor=doctor, medicine_name="Eve"', 'doctor=doctor.doctor_profile, name="Eve"')
with open(f, 'w') as fp: fp.write(c)

# Fix test_patients.py payload (force injection since previous one might have missed due to formatting)
import re
f = 'apps/patients/tests/test_patients.py'
with open(f, 'r') as fp: c = fp.read()
c = re.sub(r'\{"name": "New Patient"\}', '{"name": "New Patient", "date_of_birth": "1990-01-01"}', c)
# In case it has newlines:
if '"date_of_birth"' not in c:
    c = c.replace('"name": "New Patient"', '"name": "New Patient",\n            "date_of_birth": "1990-01-01"')
with open(f, 'w') as fp: fp.write(c)
