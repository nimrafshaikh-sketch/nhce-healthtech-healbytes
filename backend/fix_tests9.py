import glob
import re

# 1. apps/alerts/serializers.py
f = 'apps/alerts/serializers.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('"recipient_role"', '"recipient_type"')
c = c.replace("'recipient_role'", "'recipient_type'")
with open(f, 'w') as fp: fp.write(c)

# 2. apps/medications/tasks.py
f = 'apps/medications/tasks.py'
with open(f, 'r') as fp: c = fp.read()
# Replace is_active=True with end_date__isnull=True
c = c.replace('is_active=True,', 'end_date__isnull=True,')
with open(f, 'w') as fp: fp.write(c)

# 3. apps/notifications/services.py
f = 'apps/notifications/services.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('doctor.get_full_name()', 'doctor.user.name')
with open(f, 'w') as fp: fp.write(c)

# Let's check apps/alerts/tests/test_alerts.py in case we missed any `recipient_role`
f = 'apps/alerts/tests/test_alerts.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('recipient_role="doctor"', 'recipient_type="DOCTOR"')
c = c.replace('recipient_role="doctor_and_caretaker"', 'recipient_type="DOCTOR"')
with open(f, 'w') as fp: fp.write(c)
