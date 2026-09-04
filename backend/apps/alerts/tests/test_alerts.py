from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.alerts.models import Alert
from apps.core.test_utils import auth_headers, make_doctor
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
