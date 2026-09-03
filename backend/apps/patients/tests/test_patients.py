from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor
from apps.patients.models import Patient


class PatientApiTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.other_doctor = make_doctor(email="other@example.com", username="other")
        self.headers = auth_headers(self.doctor)

    def test_doctor_can_add_and_list_own_patients(self):
        resp = self.client.post(reverse("patient-list-create"), {"name": "Carol", "date_of_birth": "1990-01-01"}, format="json", **self.headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        resp = self.client.get(reverse("patient-list-create"), **self.headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

    def test_doctor_cannot_see_other_doctors_patients(self):
        Patient.objects.create(doctor=self.other_doctor.doctor_profile, name="NotMine", date_of_birth="1990-01-01")
        resp = self.client.get(reverse("patient-list-create"), **self.headers)
        self.assertEqual(resp.data["count"], 0)

    def test_doctor_cannot_access_other_doctors_patient_detail(self):
        p = Patient.objects.create(doctor=self.other_doctor.doctor_profile, name="NotMine", date_of_birth="1990-01-01")
        resp = self.client.get(reverse("patient-detail", args=[p.id]), **self.headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
