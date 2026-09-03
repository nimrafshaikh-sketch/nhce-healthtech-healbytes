from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor, make_receptionist
from apps.invitations.models import InvitationCode
from apps.patients.models import Patient


class InvitationFlowTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.headers = auth_headers(self.doctor)

    def test_invitation_code_expires_in_15_minutes(self):
        from django.conf import settings
        from django.utils import timezone
        self.assertEqual(settings.INVITATION_CODE_EXPIRY_MINUTES, 15)
        gen_resp = self.client.post(
            reverse("invitation-generate"), {"patient": {"full_name": "Zoe"}}, format="json", **self.headers,
        )
        invitation = InvitationCode.objects.get(code=gen_resp.data["code"])
        delta = invitation.expires_at - timezone.now()
        self.assertAlmostEqual(delta.total_seconds(), 15 * 60, delta=5)

    def test_generate_invitation_for_new_patient(self):
        url = reverse("invitation-generate")
        payload = {"patient": {"full_name": "John Smith", "caretaker_name": "Jane Smith",
                                "caretaker_phone_number": "1234567890"}}
        resp = self.client.post(url, payload, format="json", **self.headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(len(resp.data["code"]), 8)
        self.assertTrue(Patient.objects.filter(full_name="John Smith", doctor=self.doctor).exists())

    def test_redeem_invitation_creates_and_links_patient_account(self):
        gen_resp = self.client.post(
            reverse("invitation-generate"),
            {"patient": {"full_name": "Alice"}}, format="json", **self.headers,
        )
        code = gen_resp.data["code"]

        redeem_resp = self.client.post(reverse("invitation-redeem"), {
            "code": code, "email": "alice@example.com", "username": "alice", "password": "StrongPass123!",
        }, format="json")
        self.assertEqual(redeem_resp.status_code, status.HTTP_201_CREATED, redeem_resp.data)
        self.assertIn("access", redeem_resp.data)

        patient = Patient.objects.get(full_name="Alice")
        self.assertTrue(patient.is_linked)
        self.assertEqual(patient.user.email, "alice@example.com")

        invitation = InvitationCode.objects.get(code=code)
        self.assertTrue(invitation.is_used)

    def test_redeem_used_code_fails(self):
        gen_resp = self.client.post(
            reverse("invitation-generate"),
            {"patient": {"full_name": "Bob"}}, format="json", **self.headers,
        )
        code = gen_resp.data["code"]
        redeem_payload = {"code": code, "email": "bob@example.com", "username": "bob", "password": "StrongPass123!"}
        self.client.post(reverse("invitation-redeem"), redeem_payload, format="json")

        second_payload = {**redeem_payload, "email": "bob2@example.com", "username": "bob2"}
        resp = self.client.post(reverse("invitation-redeem"), second_payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_code_rejected(self):
        resp = self.client.post(reverse("invitation-redeem"), {
            "code": "BADCODE1", "email": "x@example.com", "username": "x", "password": "StrongPass123!",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patient_cannot_generate_invitation(self):
        from apps.core.test_utils import make_patient_user
        patient_user = make_patient_user()
        resp = self.client.post(reverse("invitation-generate"), {"patient": {"full_name": "X"}},
                                 format="json", **auth_headers(patient_user))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class ReceptionistInvitationReuseTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.receptionist = make_receptionist()
        self.reception_headers = auth_headers(self.receptionist)

    def test_receptionist_generates_invite_for_existing_patient_owned_by_doctor(self):
        patient = Patient.objects.create(doctor=self.doctor, full_name="Reception Made Me")
        resp = self.client.post(
            reverse("invitation-generate"), {"patient_id": patient.id}, format="json", **self.reception_headers,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        invitation = InvitationCode.objects.get(code=resp.data["code"])
        # invitation belongs to the patient's assigned doctor, not the receptionist
        self.assertEqual(invitation.doctor_id, self.doctor.id)

    def test_receptionist_cannot_use_inline_patient_creation(self):
        resp = self.client.post(
            reverse("invitation-generate"), {"patient": {"full_name": "Nope"}}, format="json",
            **self.reception_headers,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_receptionist_generate_for_nonexistent_patient_id_is_400_not_500(self):
        resp = self.client.post(
            reverse("invitation-generate"), {"patient_id": 999999}, format="json", **self.reception_headers,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
