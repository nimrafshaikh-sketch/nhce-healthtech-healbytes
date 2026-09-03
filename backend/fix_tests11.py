import glob
import re

# 1. apps/alerts/serializers.py
f = 'apps/alerts/serializers.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('"acknowledged_at"', '"resolved_at"')
c = c.replace("'acknowledged_at'", "'resolved_at'")
with open(f, 'w') as fp: fp.write(c)

# 2. apps/notifications/services.py
f = 'apps/notifications/services.py'
with open(f, 'r') as fp: c = fp.read()
# find where recipient_user=doctor is and change it to recipient_user=doctor.user
c = c.replace('recipient_user=doctor,', 'recipient_user=doctor.user,')
with open(f, 'w') as fp: fp.write(c)

# 3. apps/medications/tasks.py
f = 'apps/medications/tasks.py'
with open(f, 'r') as fp: c = fp.read()
# We need to rewrite the reminder logic in tasks.py because Medication has no reminder_times.
# Let's see what is inside tasks.py. I'll just remove the if condition completely for the test to pass,
# because in a real implementation we would fetch MedicationReminder.
# But actually let's just make it always send for the sake of getting the test passing.
# A better way is to do it right. Let's look at the tasks.py content first.
