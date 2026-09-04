import glob
import re

f = 'apps/medications/tests/test_medications.py'
with open(f, 'r') as fp: c = fp.read()

# For MedicationReminderTaskTests.test_dispatch_due_reminders_creates_log_and_notification
c = c.replace('from apps.medications.models import Medication, MedicationAdherence', 'from apps.medications.models import Medication, MedicationAdherence, MedicationReminder')

creation_code = """        med = Medication.objects.create(
            patient=patient, prescribed_by=doctor, medicine_name="Insulin", dosage="10u",
            frequency_per_day=1, start_date=now.date(),
        )
        MedicationReminder.objects.create(medication=med, reminder_time=now.time(), is_active=True)"""

c = re.sub(r'        med = Medication\.objects\.create\([^)]*?\)', creation_code, c, flags=re.DOTALL)

with open(f, 'w') as fp: fp.write(c)
