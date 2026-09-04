from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment
from apps.core.test_utils import auth_headers, make_doctor, make_patient_user, make_receptionist
from apps.notifications.models import Notification
from apps.patients.models import Patient


class AppointmentApiTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.other_doctor = make_doctor(email="other@example.com", username="other")
        self.receptionist = make_receptionist()
        self.patient_user = make_patient_user()
        self.patient = Patient.objects.create(doctor=self.doctor, full_name="Lena", user=self.patient_user)
        self.doctor_headers = auth_headers(self.doctor)
        self.other_doctor_headers = auth_headers(self.other_doctor)
        self.reception_headers = auth_headers(self.receptionist)
        self.patient_headers = auth_headers(self.patient_user)
        self.when = (timezone.now() + timezone.timedelta(days=1)).isoformat()

    def test_receptionist_books_appointment(self):
        payload = {"patient": self.patient.id, "doctor": self.doctor.id, "scheduled_at": self.when,
                    "reason": "Follow-up"}
        resp = self.client.post(reverse("appointment-list-create"), payload, format="json", **self.reception_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        appt = Appointment.objects.get(id=resp.data["id"])
        self.assertEqual(appt.created_by_id, self.receptionist.id)
        self.assertEqual(appt.status, "scheduled")

    def test_receptionist_booking_notifies_both_doctor_and_patient(self):
        payload = {"patient": self.patient.id, "doctor": self.doctor.id, "scheduled_at": self.when}
        resp = self.client.post(reverse("appointment-list-create"), payload, format="json", **self.reception_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        doctor_notif = Notification.objects.get(user=self.doctor)
        self.assertEqual(doctor_notif.notification_type, Notification.NotificationType.APPOINTMENT)
        patient_notif = Notification.objects.get(user=self.patient_user)
        self.assertEqual(patient_notif.notification_type, Notification.NotificationType.APPOINTMENT)

    def test_doctor_booking_own_appointment_only_notifies_patient_not_self(self):
        payload = {"patient": self.patient.id, "doctor": self.doctor.id, "scheduled_at": self.when}
        resp = self.client.post(reverse("appointment-list-create"), payload, format="json", **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        self.assertFalse(Notification.objects.filter(user=self.doctor).exists())
        self.assertTrue(Notification.objects.filter(user=self.patient_user).exists())

    def test_doctor_books_own_patient_appointment(self):
        payload = {"patient": self.patient.id, "doctor": self.doctor.id, "scheduled_at": self.when}
        resp = self.client.post(reverse("appointment-list-create"), payload, format="json", **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def test_doctor_cannot_book_for_someone_elses_patient(self):
        payload = {"patient": self.patient.id, "doctor": self.other_doctor.id, "scheduled_at": self.when}
        resp = self.client.post(reverse("appointment-list-create"), payload, format="json",
                                 **self.other_doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_cannot_book_appointment_assigned_to_another_doctor(self):
        payload = {"patient": self.patient.id, "doctor": self.other_doctor.id, "scheduled_at": self.when}
        resp = self.client.post(reverse("appointment-list-create"), payload, format="json", **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patient_cannot_book_appointment(self):
        payload = {"patient": self.patient.id, "doctor": self.doctor.id, "scheduled_at": self.when}
        resp = self.client.post(reverse("appointment-list-create"), payload, format="json", **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_can_reschedule_own_appointment(self):
        appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor, scheduled_at=self.when)
        new_time = (timezone.now() + timezone.timedelta(days=2)).isoformat()
        resp = self.client.patch(reverse("appointment-detail", args=[appt.id]), {"scheduled_at": new_time},
                                  format="json", **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

    def test_doctor_cannot_modify_someone_elses_appointment(self):
        appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor, scheduled_at=self.when)
        resp = self.client.patch(reverse("appointment-detail", args=[appt.id]), {"reason": "hack"},
                                  format="json", **self.other_doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_receptionist_can_update_any_appointment(self):
        appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor, scheduled_at=self.when)
        resp = self.client.patch(reverse("appointment-detail", args=[appt.id]), {"status": "completed"},
                                  format="json", **self.reception_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

    def test_patient_sees_own_appointment_readonly(self):
        appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor, scheduled_at=self.when)
        resp = self.client.get(reverse("appointment-detail", args=[appt.id]), **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.client.patch(reverse("appointment-detail", args=[appt.id]), {"reason": "nope"},
                                  format="json", **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_confirms_own_scheduled_appointment(self):
        appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor, scheduled_at=self.when)
        resp = self.client.post(reverse("appointment-confirm", args=[appt.id]), **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        appt.refresh_from_db()
        self.assertEqual(appt.status, "confirmed")

    def test_patient_cannot_confirm_twice(self):
        appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor, scheduled_at=self.when,
                                            status="confirmed")
        resp = self.client.post(reverse("appointment-confirm", args=[appt.id]), **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patient_cancels_own_appointment(self):
        appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor, scheduled_at=self.when)
        resp = self.client.post(reverse("appointment-cancel", args=[appt.id]), **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        appt.refresh_from_db()
        self.assertEqual(appt.status, "cancelled")

    def test_patient_cannot_confirm_someone_elses_appointment(self):
        other_patient_user = make_patient_user(email="other_patient@example.com")
        other_patient = Patient.objects.create(doctor=self.doctor, full_name="Not You", user=other_patient_user)
        appt = Appointment.objects.create(patient=other_patient, doctor=self.doctor, scheduled_at=self.when)
        resp = self.client.post(reverse("appointment-confirm", args=[appt.id]), **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_doctor_list_scoped_to_own(self):
        Appointment.objects.create(patient=self.patient, doctor=self.doctor, scheduled_at=self.when)
        other_patient_user = make_patient_user(email="p2@example.com")
        other_patient = Patient.objects.create(doctor=self.other_doctor, full_name="P2", user=other_patient_user)
        Appointment.objects.create(patient=other_patient, doctor=self.other_doctor, scheduled_at=self.when)

        resp = self.client.get(reverse("appointment-list-create"), **self.doctor_headers)
        self.assertEqual(resp.data["count"], 1)

        resp = self.client.get(reverse("appointment-list-create"), **self.reception_headers)
        self.assertEqual(resp.data["count"], 2)
