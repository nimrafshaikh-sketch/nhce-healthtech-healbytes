from django.core import mail
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.alerts.models import Alert
from apps.alerts.tasks import route_alert_for_checkin
from apps.checkins.models import DailyCheckin
from apps.core.test_utils import auth_headers, make_doctor, make_patient_user
from apps.patients.models import Patient


class AlertApiTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.patient = Patient.objects.create(doctor=self.doctor, full_name="Grace")
        self.alert = Alert.objects.create(
            patient=self.patient, severity="high", recipient_role="doctor_and_caretaker", reason="test",
        )
        self.headers = auth_headers(self.doctor)

    def test_list_alerts(self):
        resp = self.client.get(reverse("alert-list"), **self.headers)
        self.assertEqual(resp.data["count"], 1)

    def test_acknowledge_alert(self):
        resp = self.client.post(reverse("alert-acknowledge", args=[self.alert.id]), **self.headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "acknowledged")

    def test_resolve_alert(self):
        resp = self.client.post(reverse("alert-resolve", args=[self.alert.id]), **self.headers)
        self.assertEqual(resp.data["status"], "resolved")


class RouteAlertForCheckinTaskTests(TestCase):
    """apps.alerts.tasks.route_alert_for_checkin: the Celery task that turns
    a risky check-in into an Alert and (for HIGH) a doctor email. Runs
    synchronously here via CELERY_TASK_ALWAYS_EAGER (config/settings/test.py).
    """

    def setUp(self):
        self.doctor = make_doctor()
        patient_user = make_patient_user()
        self.patient = Patient.objects.create(
            doctor=self.doctor, full_name="Nora", date_of_birth="1990-01-01", user=patient_user,
        )

    def _checkin(self, risk_level):
        return DailyCheckin.objects.create(patient=self.patient, ai_risk_level=risk_level)

    def test_high_risk_checkin_creates_alert_and_sends_doctor_email(self):
        checkin = self._checkin(DailyCheckin.RiskLevel.HIGH)

        result = route_alert_for_checkin(checkin.id)

        self.assertTrue(result["alert_created"])
        alert = Alert.objects.get(id=result["alert_id"])
        self.assertEqual(alert.severity, Alert.Severity.HIGH)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.doctor.email])
        alert.refresh_from_db()
        self.assertTrue(alert.email_sent)

    def test_running_task_twice_for_same_checkin_does_not_duplicate_alert_or_email(self):
        checkin = self._checkin(DailyCheckin.RiskLevel.HIGH)

        first = route_alert_for_checkin(checkin.id)
        second = route_alert_for_checkin(checkin.id)

        self.assertTrue(first["alert_created"])
        self.assertFalse(second["alert_created"])
        self.assertEqual(second["alert_id"], first["alert_id"])
        self.assertEqual(Alert.objects.filter(checkin=checkin).count(), 1)
        # Only the first run's dispatch should have sent mail.
        self.assertEqual(len(mail.outbox), 1)

    def test_missing_doctor_email_is_logged_not_fabricated_or_crashed(self):
        self.doctor.email = ""
        self.doctor.save(update_fields=["email"])
        checkin = self._checkin(DailyCheckin.RiskLevel.HIGH)

        result = route_alert_for_checkin(checkin.id)

        self.assertTrue(result["alert_created"])
        alert = Alert.objects.get(id=result["alert_id"])
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(alert.email_sent)
        self.assertTrue(alert.email_error)  # failure was recorded, not silently dropped
        from apps.notifications.models import EmailNotificationLog
        log = EmailNotificationLog.objects.get(alert=alert)
        self.assertFalse(log.sent)
        self.assertEqual(log.recipient_email, "")  # never fabricated
