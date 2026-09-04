import glob
import re

# 1. apps/medications/views.py
f = 'apps/medications/views.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('.doctor_profile.doctor_profile', '.doctor_profile')
with open(f, 'w') as fp: fp.write(c)

# 2. apps/medications/tests/test_medications.py
f = 'apps/medications/tests/test_medications.py'
with open(f, 'r') as fp: c = fp.read()
c = re.sub(r',\s*reminder_times=\[.*?\]', '', c)
with open(f, 'w') as fp: fp.write(c)

# 3. apps/notifications/services.py
f = 'apps/notifications/services.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('alert.get_risk_level_display()', 'alert.risk_level')
with open(f, 'w') as fp: fp.write(c)
