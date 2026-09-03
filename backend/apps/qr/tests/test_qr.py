from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor, make_patient_user
from apps.patients.models import Patient
from apps.qr.tokens import generate_qr_token


class QRApiTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.other_doctor = make_doctor(email="other@example.com", username="other")
        self.patient_user = make_patient_user()
        self.patient = Patient.objects.create(doctor=self.doctor, full_name="Hank", user=self.patient_user)
        self.patient_headers = auth_headers(self.patient_user)
        self.doctor_headers = auth_headers(self.doctor)
        self.other_doctor_headers = auth_headers(self.other_doctor)

    def test_patient_generates_qr_token(self):
        resp = self.client.post(reverse("qr-generate"), **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("token", resp.data)

    def test_assigned_doctor_can_verify_qr(self):
        gen = self.client.post(reverse("qr-generate"), **self.patient_headers)
        resp = self.client.post(reverse("qr-verify"), {"token": gen.data["token"]}, format="json", **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["patient"]["id"], self.patient.id)

    def test_unassigned_doctor_forbidden(self):
        gen = self.client.post(reverse("qr-generate"), **self.patient_headers)
        resp = self.client.post(reverse("qr-verify"), {"token": gen.data["token"]}, format="json",
                                 **self.other_doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_generated_token_expires_in_15_minutes(self):
        from django.conf import settings
        self.assertEqual(settings.QR_TOKEN_EXPIRY_MINUTES, 15)
        result = generate_qr_token(self.patient)
        from django.utils import timezone
        delta = result["expires_at"] - timezone.now()
        self.assertAlmostEqual(delta.total_seconds(), 15 * 60, delta=5)

    def test_expired_token_rejected(self):
        import jwt
        from django.conf import settings
        from django.utils import timezone

        expired_payload = {
            "type": "patient_qr", "patient_id": self.patient.id,
            "iat": int((timezone.now() - timezone.timedelta(minutes=10)).timestamp()),
            "exp": int((timezone.now() - timezone.timedelta(minutes=1)).timestamp()),
        }
        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm="HS256")
        resp = self.client.post(reverse("qr-verify"), {"token": expired_token}, format="json", **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patient_cannot_verify(self):
        resp = self.client.post(reverse("qr-verify"), {"token": "x"}, format="json", **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
