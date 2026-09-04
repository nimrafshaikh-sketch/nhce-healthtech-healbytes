from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor, make_lab_tech, make_patient_user, make_receptionist
from apps.qr.models import QRAccessGrant, QRScanLog
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
        # The assigned doctor already has standing access - no grant needed.
        self.assertFalse(QRAccessGrant.objects.filter(patient=self.patient, doctor=self.doctor).exists())

    def test_unassigned_doctor_with_valid_qr_gets_a_bounded_grant_not_permanent_access(self):
        """This is the multi-doctor consult path: a doctor who is NOT the
        patient's assigned doctor can still verify a genuine, currently
        valid QR (the patient presenting it is the consent event) - but the
        result must be a bounded QRAccessGrant, never unconditional/
        permanent access, and it must never reassign the patient."""
        gen = self.client.post(reverse("qr-generate"), **self.patient_headers)
        resp = self.client.post(reverse("qr-verify"), {"token": gen.data["token"]}, format="json",
                                 **self.other_doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["patient"]["id"], self.patient.id)

        grant = QRAccessGrant.objects.filter(patient=self.patient, doctor=self.other_doctor).first()
        self.assertIsNotNone(grant, "expected a QRAccessGrant to be created for the unassigned doctor")
        self.assertTrue(grant.is_active())

        from django.conf import settings
        from django.utils import timezone
        expected_expiry = timezone.now() + timezone.timedelta(minutes=settings.QR_ACCESS_GRANT_MINUTES)
        self.assertAlmostEqual(
            (grant.expires_at - expected_expiry).total_seconds(), 0, delta=5,
        )

        # The patient's primary-doctor assignment must be completely untouched.
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.doctor_id, self.doctor.id)

    def test_grant_defaults_to_exactly_10_minutes(self):
        """Part 13/25 requirement: the consultation window is EXACTLY 10
        minutes by default (minutes, never accidentally hours)."""
        from django.conf import settings
        self.assertEqual(settings.QR_ACCESS_GRANT_MINUTES, 10)

    def test_expired_grant_no_longer_authorizes_document_or_rag_access(self):
        """A grant that has aged past its expiry must stop authorizing
        access - has_active_grant must be a live, not one-time, check."""
        from django.utils import timezone

        grant = QRAccessGrant.objects.create(
            patient=self.patient, doctor=self.other_doctor,
            expires_at=timezone.now() - timezone.timedelta(hours=1),
        )
        self.assertFalse(grant.is_active())
        self.assertFalse(QRAccessGrant.has_active_grant(patient=self.patient, doctor=self.other_doctor))

    def test_grant_exact_10_minute_boundary(self):
        """T0 = grant created (now). T+9min = still active. T+10min = expired.
        T+11min = expired. Verified by constructing grants at each offset
        relative to 'now', rather than freezing global time (no freezegun
        dependency in this project)."""
        from django.utils import timezone

        now = timezone.now()

        # Simulate "T+9 minutes" into a 10-minute grant: 1 minute of validity
        # remains from 'now', so it must still be active.
        still_valid = QRAccessGrant.objects.create(
            patient=self.patient, doctor=self.other_doctor,
            expires_at=now + timezone.timedelta(minutes=1),
        )
        self.assertTrue(still_valid.is_active())

        # Simulate "T+10 minutes": the grant's validity window has just closed.
        exactly_expired = QRAccessGrant.objects.create(
            patient=self.patient, doctor=self.other_doctor,
            expires_at=now,
        )
        self.assertFalse(exactly_expired.is_active(), "a grant expiring at/before now must be expired")

        # Simulate "T+11 minutes": clearly expired.
        past_expired = QRAccessGrant.objects.create(
            patient=self.patient, doctor=self.other_doctor,
            expires_at=now - timezone.timedelta(minutes=1),
        )
        self.assertFalse(past_expired.is_active())

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

    def test_receptionist_cannot_verify_qr(self):
        # Locked scope: QR is clinical-history access, receptionist has none - unchanged from original plan.
        receptionist = make_receptionist()
        gen = self.client.post(reverse("qr-generate"), **self.patient_headers)
        resp = self.client.post(reverse("qr-verify"), {"token": gen.data["token"]}, format="json",
                                 **auth_headers(receptionist))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_lab_tech_cannot_verify_qr(self):
        lab_tech = make_lab_tech()
        gen = self.client.post(reverse("qr-generate"), **self.patient_headers)
        resp = self.client.post(reverse("qr-verify"), {"token": gen.data["token"]}, format="json",
                                 **auth_headers(lab_tech))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_every_outcome_is_logged(self):
        # success
        gen = self.client.post(reverse("qr-generate"), **self.patient_headers)
        token = gen.data["token"]
        self.client.post(reverse("qr-verify"), {"token": token}, format="json", **self.doctor_headers)
        self.assertTrue(QRScanLog.objects.filter(patient=self.patient, success=True).exists())

        # other doctor with valid token logs success AND receives a bounded grant
        self.client.post(reverse("qr-verify"), {"token": token}, format="json", **self.other_doctor_headers)
        self.assertTrue(QRScanLog.objects.filter(
            patient=self.patient, scanned_by=self.other_doctor, success=True).exists())
        self.assertTrue(QRAccessGrant.objects.filter(
            patient=self.patient, doctor=self.other_doctor).exists())

        # malformed token - genuinely unknown patient, still logged with patient=None
        before = QRScanLog.objects.count()
        self.client.post(reverse("qr-verify"), {"token": "not-a-real-token"}, format="json", **self.doctor_headers)
        self.assertEqual(QRScanLog.objects.count(), before + 1)
        self.assertTrue(QRScanLog.objects.filter(patient__isnull=True, success=False).exists())

        # patient not found (well-formed token, deleted patient)
        import jwt
        from django.conf import settings as dj_settings
        from django.utils import timezone
        fake_payload = {
            "type": "patient_qr", "patient_id": 999999,
            "iat": int(timezone.now().timestamp()),
            "exp": int((timezone.now() + timezone.timedelta(minutes=5)).timestamp()),
        }
        fake_token = jwt.encode(fake_payload, dj_settings.SECRET_KEY, algorithm="HS256")
        before = QRScanLog.objects.count()
        self.client.post(reverse("qr-verify"), {"token": fake_token}, format="json", **self.doctor_headers)
        self.assertEqual(QRScanLog.objects.count(), before + 1)
        self.assertTrue(QRScanLog.objects.filter(
            patient__isnull=True, failure_reason__icontains="999999").exists())

    def test_expired_token_still_logged_with_patient_attributed(self):
        import jwt
        from django.conf import settings
        from django.utils import timezone

        expired_payload = {
            "type": "patient_qr", "patient_id": self.patient.id,
            "iat": int((timezone.now() - timezone.timedelta(minutes=20)).timestamp()),
            "exp": int((timezone.now() - timezone.timedelta(minutes=1)).timestamp()),
        }
        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm="HS256")
        before = QRScanLog.objects.count()
        resp = self.client.post(reverse("qr-verify"), {"token": expired_token}, format="json", **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(QRScanLog.objects.count(), before + 1)
        self.assertTrue(QRScanLog.objects.filter(
            patient=self.patient, success=False, failure_reason__icontains="expired").exists())
