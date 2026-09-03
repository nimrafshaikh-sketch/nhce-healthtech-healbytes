import glob

# Fix test_medications.py
f = 'apps/medications/tests/test_medications.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('Patient.objects.create(doctor=self.doctor.doctor_profile, medicine_name="Dana",', 'Patient.objects.create(doctor=self.doctor.doctor_profile, name="Dana",')
c = c.replace('MedicationReminderLog', 'MedicationAdherence')
with open(f, 'w') as fp: fp.write(c)

# Fix test_doctor_email.py
f = 'apps/notifications/tests/test_doctor_email.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('severity="high"', 'risk_level="HIGH"')
c = c.replace('severity="medium"', 'risk_level="MEDIUM"')
c = c.replace('recipient_role="doctor_and_caretaker"', 'recipient_type="DOCTOR"')
c = c.replace('recipient_role="doctor"', 'recipient_type="DOCTOR"')
with open(f, 'w') as fp: fp.write(c)

# Fix test_patients.py payload
f = 'apps/patients/tests/test_patients.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('"name": "New Patient"', '"name": "New Patient", "date_of_birth": "1990-01-01"')
c = c.replace('{"name": "New Patient"}', '{"name": "New Patient", "date_of_birth": "1990-01-01"}')
with open(f, 'w') as fp: fp.write(c)
