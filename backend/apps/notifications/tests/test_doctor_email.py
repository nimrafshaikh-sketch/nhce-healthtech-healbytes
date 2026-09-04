from django.core import mail
from django.test import TestCase

from apps.alerts.models import Alert
from apps.core.test_utils import make_doctor, make_patient_user
from apps.notifications.models import EmailNotificationLog
from apps.notifications.services import send_doctor_alert_email
from apps.patients.models import Patient


class DoctorAlertEmailTests(TestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.patient = Patient.objects.create(doctor=self.doctor.doctor_profile, name="Kate", date_of_birth="1990-01-01")

    def test_high_severity_alert_emails_doctor(self):
        alert = Alert.objects.create(
            patient=self.patient, risk_level="HIGH", recipient_type="DOCTOR", reason="urgent",
        )
        log = send_doctor_alert_email(alert)
        self.assertIsNotNone(log)
        self.assertTrue(log.sent)
        self.assertEqual(mail.outbox[0].to, [self.doctor.email])

        alert.refresh_from_db()
        self.assertTrue(alert.email_sent)
        self.assertIsNotNone(alert.email_sent_at)

    def test_log_recorded_even_though_only_high_should_call_this(self):
        alert = Alert.objects.create(
            patient=self.patient, risk_level="MEDIUM", recipient_type="DOCTOR", reason="fyi",
        )
        # service itself doesn't gate by severity - that's rules.should_email_doctor's job,
        # enforced by the caller (apps.alerts.tasks). Calling it directly still sends + logs.
        log = send_doctor_alert_email(alert)
        self.assertTrue(log.sent)
        self.assertEqual(EmailNotificationLog.objects.filter(alert=alert, recipient_type="doctor").count(), 1)
