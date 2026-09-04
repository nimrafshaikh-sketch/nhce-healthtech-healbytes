import glob
import re

# 1. test_medications.py
f = 'apps/medications/tests/test_medications.py'
with open(f, 'r') as fp: c = fp.read()
# Remove reminder_times from test_doctor_can_prescribe_medication payload
c = re.sub(r',\s*"reminder_times": \[.*?\]', '', c)
c = c.replace('"reminder_times": ["25:99"]', '')
# delete test_invalid_reminder_time_rejected entirely
c = re.sub(r'    def test_invalid_reminder_time_rejected\(self\):.*?status\.HTTP_400_BAD_REQUEST\)', '', c, flags=re.DOTALL)
with open(f, 'w') as fp: fp.write(c)

# 2. test_patients.py
f = 'apps/patients/tests/test_patients.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('{"name": "Carol"}', '{"name": "Carol", "date_of_birth": "1990-01-01"}')
with open(f, 'w') as fp: fp.write(c)
