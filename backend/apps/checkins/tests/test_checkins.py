from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor, make_lab_tech, make_patient_user, make_receptionist
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
            doctor=self.doctor, full_name="Frank", user=self.patient_user,
            caretaker_name="Cara", caretaker_email="cara@example.com",
        )
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

    def test_omitted_checkin_date_defaults_to_today_and_rejects_duplicate(self):
        payload = {
            "symptoms": [{"name": "Fever", "severity": "SEVERE"}],
            "mood": "not_good",
            "pain_level": 8,
            "duration": "SEVERAL_DAYS",
            "medication_adherence": "MISSED_MULTIPLE",
            "notes": "Started high fever",
        }
        r1 = self.client.post(reverse("checkin-list-create"), payload, format="json", **self.patient_headers)
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED, r1.data)
        self.assertEqual(r1.data["symptom_duration"], "SEVERAL_DAYS")
        self.assertEqual(r1.data["medication_adherence"], "MISSED_MULTIPLE")

        r2 = self.client.post(reverse("checkin-list-create"), payload, format="json", **self.patient_headers)
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

        listed = self.client.get(reverse("checkin-list-create"), **self.patient_headers)
        self.assertEqual(listed.data["count"], 1)
        row = listed.data["results"][0]
        self.assertEqual(row["patient"], self.patient.id)
        self.assertEqual(row["symptom_duration"], "SEVERAL_DAYS")
        self.assertEqual(row["medication_adherence"], "MISSED_MULTIPLE")
        self.assertEqual(row["symptoms"], [{"name": "Fever", "severity": "SEVERE"}])

    def test_invalid_patient_query_param_fails_closed(self):
        self.client.post(reverse("checkin-list-create"), {"checkin_date": "2026-01-08", "symptoms": []}, format="json", **self.patient_headers)
        resp = self.client.get(f"{reverse('checkin-list-create')}?patient=abc", **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)

    def test_cross_patient_and_non_clinical_role_isolation(self):
        r1 = self.client.post(reverse("checkin-list-create"), {"checkin_date": "2026-01-09", "symptoms": ["Fatigue"]}, format="json", **self.patient_headers)
        checkin_id = r1.data["id"]

        other_patient_user = make_patient_user(email="other_pat@example.com")
        Patient.objects.create(doctor=self.doctor, full_name="Other", user=other_patient_user)
        other_pat_headers = auth_headers(other_patient_user)

        other_doc = make_doctor(email="other_doc@example.com")
        other_doc_headers = auth_headers(other_doc)

        rec_headers = auth_headers(make_receptionist())
        lab_headers = auth_headers(make_lab_tech())

        # Patient isolation
        self.assertEqual(self.client.get(reverse("checkin-list-create"), **other_pat_headers).data["count"], 0)
        self.assertEqual(self.client.get(reverse("checkin-detail", args=[checkin_id]), **other_pat_headers).status_code, status.HTTP_404_NOT_FOUND)
        # Doctor isolation
        self.assertEqual(self.client.get(reverse("checkin-list-create"), **other_doc_headers).data["count"], 0)
        self.assertEqual(self.client.get(reverse("checkin-detail", args=[checkin_id]), **other_doc_headers).status_code, status.HTTP_404_NOT_FOUND)
        # Receptionist and Lab Tech have no check-in access
        self.assertEqual(self.client.get(reverse("checkin-list-create"), **rec_headers).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(reverse("checkin-list-create"), **lab_headers).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(reverse("checkin-detail", args=[checkin_id]), **rec_headers).status_code, status.HTTP_403_FORBIDDEN)
