import re

# 1. apps/alerts/serializers.py
f = 'apps/alerts/serializers.py'
with open(f, 'r') as fp: c = fp.read()
# Replace patient.full_name with patient.name
c = c.replace('"patient.full_name"', '"patient.name"')
# Fields update: "email_sent", "email_sent_at", "acknowledged_at" -> removed
c = c.replace('"acknowledged_at",', '')
c = c.replace('"email_sent", "email_sent_at", ', '')
with open(f, 'w') as fp: fp.write(c)

# 2. apps/notifications/services.py
f = 'apps/notifications/services.py'
with open(f, 'r') as fp: c = fp.read()
# fix recipient_user
c = c.replace('recipient_user=doctor,', 'recipient_user=doctor.user,')

# fix alert.email_sent etc.
# Lines 129-136
bad_code = """    alert.email_sent = log.sent
    alert.email_error = log.error
    if log.sent:
        from django.utils import timezone
        alert.email_sent_at = timezone.now()
        alert.save(update_fields=["email_sent", "email_sent_at", "email_error"])
    else:
        alert.save(update_fields=["email_sent", "email_error"])"""
c = c.replace(bad_code, "")
with open(f, 'w') as fp: fp.write(c)
