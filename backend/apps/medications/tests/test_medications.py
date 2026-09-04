from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor, make_patient_user
from apps.patients.models import Patient


class MedicationApiTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.patient_user = make_patient_user()
        self.patient = Patient.objects.create(doctor=self.doctor, full_name="Dana", user=self.patient_user)
        self.doctor_headers = auth_headers(self.doctor)
        self.patient_headers = auth_headers(self.patient_user)

    def test_doctor_can_prescribe_medication(self):
        payload = {
            "patient": self.patient.id, "name": "Metformin", "dosage": "500mg",
            "frequency": "twice_daily", "start_date": "2026-01-01",
            "reminder_times": ["08:00", "20:00"],
        }
        resp = self.client.post(reverse("medication-list-create"), payload, format="json", **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def test_patient_cannot_prescribe(self):
        payload = {"patient": self.patient.id, "name": "X", "dosage": "1", "frequency": "once_daily",
                    "start_date": "2026-01-01"}
        resp = self.client.post(reverse("medication-list-create"), payload, format="json", **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_reminder_time_rejected(self):
        payload = {"patient": self.patient.id, "name": "X", "dosage": "1", "frequency": "once_daily",
                    "start_date": "2026-01-01", "reminder_times": ["25:99"]}
        resp = self.client.post(reverse("medication-list-create"), payload, format="json", **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patient_sees_own_medications(self):
        from apps.medications.models import Medication
        Medication.objects.create(patient=self.patient, prescribed_by=self.doctor, name="Aspirin",
                                    dosage="75mg", frequency="once_daily", start_date="2026-01-01")
        resp = self.client.get(reverse("medication-list-create"), **self.patient_headers)
        self.assertEqual(resp.data["count"], 1)


class MedicationReminderTaskTests(APITestCase):
    def test_dispatch_due_reminders_creates_log_and_notification(self):
        from django.utils import timezone

        from apps.medications.models import Medication, MedicationReminderLog
        from apps.medications.tasks import dispatch_due_medication_reminders
        from apps.notifications.models import Notification

        doctor = make_doctor()
        patient_user = make_patient_user()
        patient = Patient.objects.create(doctor=doctor, full_name="Eve", user=patient_user)
        now = timezone.localtime()
        med = Medication.objects.create(
            patient=patient, prescribed_by=doctor, name="Insulin", dosage="10u",
            frequency="once_daily", start_date=now.date(), reminder_times=[now.strftime("%H:%M")],
        )

        dispatch_due_medication_reminders()

        self.assertTrue(MedicationReminderLog.objects.filter(medication=med).exists())
        self.assertTrue(Notification.objects.filter(user=patient_user, notification_type="medication_reminder").exists())

        from django.core import mail

        from apps.notifications.models import EmailNotificationLog
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [patient_user.email])
        self.assertTrue(EmailNotificationLog.objects.filter(
            medication=med, recipient_type="patient", category="medication_reminder", sent=True).exists())

        # running again in the same minute should not duplicate
        dispatch_due_medication_reminders()
        self.assertEqual(MedicationReminderLog.objects.filter(medication=med).count(), 1)
        self.assertEqual(len(mail.outbox), 1)


class AcknowledgeReminderTests(APITestCase):
    """Feature 3 integration check: patient marks a dispatched reminder as
    Taken (acknowledged), and that update is correctly linked to the right
    patient/medication - the same MedicationReminderLog row that
    apps.checkins.ai_client._build_medical_context and the analytics/AI
    summary endpoints read adherence from (see apps.patients.analytics_views
    and the AI Engine's medication_adherence module). No new adherence model
    is introduced; acknowledgment of the existing log row IS the adherence
    signal.
    """

    def setUp(self):
        self.doctor = make_doctor()
        self.patient_user = make_patient_user()
        self.patient = Patient.objects.create(doctor=self.doctor, full_name="Rae", user=self.patient_user)
        self.patient_headers = auth_headers(self.patient_user)

    def _reminder_log(self, patient=None):
        from django.utils import timezone

        from apps.medications.models import Medication, MedicationReminderLog

        patient = patient or self.patient
        med = Medication.objects.create(
            patient=patient, prescribed_by=self.doctor, name="Lisinopril", dosage="10mg",
            frequency="once_daily", start_date="2026-01-01", reminder_times=["08:00"],
        )
        return MedicationReminderLog.objects.create(medication=med, scheduled_for=timezone.now())

    def test_patient_can_acknowledge_own_reminder(self):
        log = self._reminder_log()

        resp = self.client.post(reverse("reminder-acknowledge", args=[log.id]), **self.patient_headers)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        log.refresh_from_db()
        self.assertIsNotNone(log.acknowledged_at)
        # Correctly linked to this patient's own medication - the same row
        # the adherence calculation reads from.
        self.assertEqual(log.medication.patient_id, self.patient.id)

    def test_patient_cannot_acknowledge_another_patients_reminder(self):
        other_user = make_patient_user(email="other@example.com", username="other")
        other_patient = Patient.objects.create(doctor=self.doctor, full_name="Sam", user=other_user)
        log = self._reminder_log(patient=other_patient)

        resp = self.client.post(reverse("reminder-acknowledge", args=[log.id]), **self.patient_headers)

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        log.refresh_from_db()
        self.assertIsNone(log.acknowledged_at)
