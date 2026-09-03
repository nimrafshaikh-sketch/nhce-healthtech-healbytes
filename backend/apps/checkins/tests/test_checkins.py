from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor, make_patient_user
from apps.patients.models import Patient


def ai_result(risk_level, **overrides):
    base = {
        "risk_level": risk_level,
        "risk_score": 0.5,
        "reason": "test reason",
        "recommended_action": "test action",
        "notification_recipient": "doctor",
    }
    base.update(overrides)
    return base


class CheckinApiTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()  # doctor.email always set (required field)
        self.patient_user = make_patient_user()  # patient_user.email always set
        self.patient = Patient.objects.create(
            doctor=self.doctor.doctor_profile, name="Frank", user=self.patient_user,
            caretaker_name="Cara", caretaker_email="cara@example.com",
        , date_of_birth="1990-01-01")
        self.patient_headers = auth_headers(self.patient_user)
        self.doctor_headers = auth_headers(self.doctor)

    @patch("apps.checkins.ai_client.analyze_checkin")
    def test_high_risk_creates_alert_emails_doctor_and_patient_not_caretaker(self, mock_analyze):
        mock_analyze.return_value = ai_result("high", risk_score=0.95, reason="elevated symptoms")
        payload = {"checkin_date": "2026-01-01", "symptoms": ["fever"], "pain_level": 6}
        resp = self.client.post(reverse("checkin-list-create"), payload, format="json", **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        from apps.checkins.models import DailyCheckin
        checkin = DailyCheckin.objects.get(patient=self.patient)
        self.assertEqual(checkin.ai_risk_level, "high")
        self.assertEqual(checkin.ai_risk_score, 0.95)
        self.assertEqual(checkin.ai_notes, "elevated symptoms")

        from apps.alerts.models import Alert
        alert = Alert.objects.get(patient=self.patient)
        self.assertEqual(alert.severity, "high")
        self.assertEqual(alert.recipient_role, "doctor_and_caretaker")
        self.assertTrue(alert.email_sent)

        # high risk: doctor gets an email (urgent) + patient gets their own result email;
        # caretaker does NOT get an email for high (only low/medium).
        self.assertEqual(len(mail.outbox), 2)
        recipients = {tuple(m.to) for m in mail.outbox}
        self.assertIn((self.doctor.email,), recipients)
        self.assertIn((self.patient_user.email,), recipients)
        self.assertNotIn(("cara@example.com",), recipients)

    @patch("apps.checkins.ai_client.analyze_checkin")
    def test_medium_risk_emails_caretaker_and_patient_not_doctor(self, mock_analyze):
        mock_analyze.return_value = ai_result("medium")
        payload = {"checkin_date": "2026-01-06", "symptoms": ["cough"]}
        resp = self.client.post(reverse("checkin-list-create"), payload, format="json", **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        from apps.alerts.models import Alert
        alert = Alert.objects.get(patient=self.patient)
        self.assertFalse(alert.email_sent)  # medium doesn't email the doctor

        self.assertEqual(len(mail.outbox), 2)
        recipients = {tuple(m.to) for m in mail.outbox}
        self.assertIn(("cara@example.com",), recipients)
        self.assertIn((self.patient_user.email,), recipients)

        from apps.notifications.models import EmailNotificationLog
        self.assertTrue(EmailNotificationLog.objects.filter(
            patient=self.patient, recipient_type="caretaker", sent=True).exists())
        self.assertTrue(EmailNotificationLog.objects.filter(
            patient=self.patient, recipient_type="patient", category="checkin_result", sent=True).exists())

    @patch("apps.checkins.ai_client.analyze_checkin")
    def test_low_risk_no_alert_but_emails_caretaker_and_patient(self, mock_analyze):
        mock_analyze.return_value = ai_result("low")
        payload = {"checkin_date": "2026-01-07", "symptoms": []}
        resp = self.client.post(reverse("checkin-list-create"), payload, format="json", **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        from apps.alerts.models import Alert
        self.assertFalse(Alert.objects.filter(patient=self.patient).exists())
        self.assertEqual(len(mail.outbox), 2)

    def test_ai_engine_unavailable_still_saves_checkin_no_emails(self):
        # AI_ENGINE_URL is blank in test settings by default -> ai_client returns "unavailable"
        payload = {"checkin_date": "2026-01-02", "symptoms": []}
        resp = self.client.post(reverse("checkin-list-create"), payload, format="json", **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        from apps.checkins.models import DailyCheckin
        checkin = DailyCheckin.objects.get(patient=self.patient)
        self.assertEqual(checkin.ai_risk_level, "unavailable")
        self.assertIsNone(checkin.ai_risk_score)

        from apps.alerts.models import Alert
        self.assertFalse(Alert.objects.filter(patient=self.patient).exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_duplicate_checkin_same_day_rejected(self):
        payload = {"checkin_date": "2026-01-03", "symptoms": []}
        self.client.post(reverse("checkin-list-create"), payload, format="json", **self.patient_headers)
        resp = self.client.post(reverse("checkin-list-create"), payload, format="json", **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_doctor_cannot_submit_checkin(self):
        payload = {"checkin_date": "2026-01-04", "symptoms": []}
        resp = self.client.post(reverse("checkin-list-create"), payload, format="json", **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_sees_own_patients_checkins(self):
        payload = {"checkin_date": "2026-01-05", "symptoms": []}
        self.client.post(reverse("checkin-list-create"), payload, format="json", **self.patient_headers)
        resp = self.client.get(reverse("checkin-list-create"), **self.doctor_headers)
        self.assertEqual(resp.data["count"], 1)
