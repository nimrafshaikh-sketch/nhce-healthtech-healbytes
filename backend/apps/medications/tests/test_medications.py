from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor, make_patient_user
from apps.patients.models import Patient


class MedicationApiTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.patient_user = make_patient_user()
        self.patient = Patient.objects.create(doctor=self.doctor.doctor_profile, name="Dana", user=self.patient_user, date_of_birth="1990-01-01")
        self.doctor_headers = auth_headers(self.doctor)
        self.patient_headers = auth_headers(self.patient_user)

    def test_doctor_can_prescribe_medication(self):
        payload = {
            "patient": self.patient.id, "medicine_name": "Metformin", "dosage": "500mg",
            "frequency_per_day": 2, "start_date": "2026-01-01",
        }
        resp = self.client.post(reverse("medication-list-create"), payload, format="json", **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def test_patient_cannot_prescribe(self):
        payload = {"patient": self.patient.id, "medicine_name": "X", "dosage": "1", "frequency_per_day": 1,
                    "start_date": "2026-01-01"}
        resp = self.client.post(reverse("medication-list-create"), payload, format="json", **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)



    def test_patient_sees_own_medications(self):
        from apps.medications.models import Medication
        Medication.objects.create(patient=self.patient, prescribed_by=self.doctor, medicine_name="Aspirin",
                                    dosage="75mg", frequency_per_day=1, start_date="2026-01-01")
        resp = self.client.get(reverse("medication-list-create"), **self.patient_headers)
        self.assertEqual(resp.data["count"], 1)


class MedicationReminderTaskTests(APITestCase):
    def test_dispatch_due_reminders_creates_log_and_notification(self):
        from django.utils import timezone

        from apps.medications.models import Medication, MedicationAdherence, MedicationReminder
        from apps.medications.tasks import dispatch_due_medication_reminders
        from apps.notifications.models import Notification

        doctor = make_doctor()
        patient_user = make_patient_user()
        patient = Patient.objects.create(doctor=doctor.doctor_profile, name="Eve", user=patient_user, date_of_birth="1990-01-01")
        now = timezone.localtime()
        med = Medication.objects.create(
            patient=patient, prescribed_by=doctor, medicine_name="Insulin", dosage="10u",
            frequency_per_day=1, start_date=now.date(),
        )
        MedicationReminder.objects.create(medication=med, reminder_time=now.time(), is_active=True),
        )

        dispatch_due_medication_reminders()

        self.assertTrue(MedicationAdherence.objects.filter(medication=med).exists())
        self.assertTrue(Notification.objects.filter(user=patient_user, notification_type="medication_reminder").exists())

        from django.core import mail

        from apps.notifications.models import EmailNotificationLog
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [patient_user.email])
        self.assertTrue(EmailNotificationLog.objects.filter(
            medication=med, recipient_type="patient", category="medication_reminder", sent=True).exists())

        # running again in the same minute should not duplicate
        dispatch_due_medication_reminders()
        self.assertEqual(MedicationAdherence.objects.filter(medication=med).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
