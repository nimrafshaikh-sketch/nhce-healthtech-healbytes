import glob
import re

# 1. apps/alerts/serializers.py
f = 'apps/alerts/serializers.py'
with open(f, 'r') as fp: c = fp.read()
# Replace acknowledged_by with resolved_at
c = c.replace('"acknowledged_by"', '"resolved_at"')
c = c.replace("'acknowledged_by'", "'resolved_at'")
with open(f, 'w') as fp: fp.write(c)

# 2. apps/medications/tasks.py
f = 'apps/medications/tasks.py'
with open(f, 'r') as fp: c = fp.read()
# Remove reminders_enabled=True
c = c.replace('reminders_enabled=True,\n', '')
c = c.replace('        reminders_enabled=True,', '')
with open(f, 'w') as fp: fp.write(c)

# 3. apps/notifications/services.py
f = 'apps/notifications/services.py'
with open(f, 'r') as fp: c = fp.read()
# Replace alert.severity with alert.risk_level
c = c.replace('alert.severity', 'alert.risk_level')
with open(f, 'w') as fp: fp.write(c)
