from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class DoctorAuthTests(APITestCase):
    def test_doctor_register_and_login(self):
        register_url = reverse("register-doctor")
        payload = {
            "email": "doc@example.com", "name": "Dr. Doc", "username": "doc1", "password": "StrongPass123!",
            "first_name": "Jane", "last_name": "Doe", "specialization": "Cardiology",
        }
        resp = self.client.post(register_url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        login_url = reverse("login")
        resp = self.client.post(login_url, {"email": "doc@example.com", "name": "Dr. Doc", "password": "StrongPass123!"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertIn("access", resp.data)
        self.assertEqual(resp.data["user"]["role"], "doctor")

    def test_login_wrong_password_fails(self):
        self.client.post(reverse("register-doctor"), {
            "email": "doc2@example.com", "username": "doc2", "password": "StrongPass123!",
        }, format="json")
        resp = self.client.post(reverse("login"), {"email": "doc2@example.com", "password": "wrong"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_auth(self):
        resp = self.client.get(reverse("me"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
