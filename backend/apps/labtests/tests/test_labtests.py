from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor, make_lab_tech, make_patient_user, make_receptionist
from apps.labtests.models import LabTestRequest, LabTestResult
from apps.patients.models import Patient


class LabTestFlowTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.other_doctor = make_doctor(email="other@example.com", username="other")
        self.lab_tech = make_lab_tech()
        self.other_lab_tech = make_lab_tech(email="labtech2@example.com", username="labtech2")
        self.receptionist = make_receptionist()
        self.patient = Patient.objects.create(doctor=self.doctor, full_name="Mira")
        self.doctor_headers = auth_headers(self.doctor)
        self.other_doctor_headers = auth_headers(self.other_doctor)
        self.lab_headers = auth_headers(self.lab_tech)
        self.other_lab_headers = auth_headers(self.other_lab_tech)
        self.reception_headers = auth_headers(self.receptionist)

    def test_doctor_requests_lab_test_for_own_patient(self):
        payload = {"patient": self.patient.id, "test_name": "CBC", "priority": "urgent"}
        resp = self.client.post(reverse("labtest-request-list-create"), payload, format="json",
                                 **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["status"], "requested")
        self.assertIsNone(resp.data["assigned_lab_tech"])

    def test_doctor_cannot_request_for_other_doctors_patient(self):
        payload = {"patient": self.patient.id, "test_name": "CBC"}
        resp = self.client.post(reverse("labtest-request-list-create"), payload, format="json",
                                 **self.other_doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_test_name_rejected(self):
        payload = {"patient": self.patient.id, "test_name": "NOT_A_REAL_TEST"}
        resp = self.client.post(reverse("labtest-request-list-create"), payload, format="json",
                                 **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_receptionist_has_zero_access(self):
        req = LabTestRequest.objects.create(patient=self.patient, requested_by=self.doctor, test_name="CBC")
        resp = self.client.get(reverse("labtest-request-list-create"), **self.reception_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        resp = self.client.post(reverse("labtest-request-list-create"),
                                 {"patient": self.patient.id, "test_name": "CBC"}, format="json",
                                 **self.reception_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        resp = self.client.get(reverse("labtest-request-detail", args=[req.id]), **self.reception_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_lab_tech_sees_unclaimed_queue(self):
        LabTestRequest.objects.create(patient=self.patient, requested_by=self.doctor, test_name="CBC")
        resp = self.client.get(reverse("labtest-request-list-create"), **self.lab_headers)
        self.assertEqual(resp.data["count"], 1)

    def test_lab_tech_claims_request(self):
        req = LabTestRequest.objects.create(patient=self.patient, requested_by=self.doctor, test_name="CBC")
        resp = self.client.post(reverse("labtest-request-claim", args=[req.id]), **self.lab_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        req.refresh_from_db()
        self.assertEqual(req.assigned_lab_tech_id, self.lab_tech.id)
        self.assertEqual(req.status, "in_progress")

    def test_second_lab_tech_cannot_claim_already_claimed_request(self):
        req = LabTestRequest.objects.create(
            patient=self.patient, requested_by=self.doctor, test_name="CBC",
            assigned_lab_tech=self.lab_tech, status="in_progress",
        )
        resp = self.client.post(reverse("labtest-request-claim", args=[req.id]), **self.other_lab_headers)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unclaimed_request_not_visible_to_lab_tech_who_didnt_claim_it_once_claimed(self):
        req = LabTestRequest.objects.create(
            patient=self.patient, requested_by=self.doctor, test_name="CBC",
            assigned_lab_tech=self.lab_tech, status="in_progress",
        )
        resp = self.client.get(reverse("labtest-request-list-create"), **self.other_lab_headers)
        self.assertEqual(resp.data["count"], 0)

    def test_assigned_lab_tech_submits_result_completes_request(self):
        req = LabTestRequest.objects.create(
            patient=self.patient, requested_by=self.doctor, test_name="CBC",
            assigned_lab_tech=self.lab_tech, status="in_progress",
        )
        resp = self.client.post(reverse("labtest-result-create", args=[req.id]),
                                 {"result_text": "WBC 7.2, all normal"}, format="json", **self.lab_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        req.refresh_from_db()
        self.assertEqual(req.status, "completed")
        self.assertTrue(LabTestResult.objects.filter(request=req, recorded_by=self.lab_tech).exists())

    def test_unassigned_lab_tech_cannot_submit_result(self):
        req = LabTestRequest.objects.create(
            patient=self.patient, requested_by=self.doctor, test_name="CBC",
            assigned_lab_tech=self.lab_tech, status="in_progress",
        )
        resp = self.client.post(reverse("labtest-result-create", args=[req.id]),
                                 {"result_text": "sneaky"}, format="json", **self.other_lab_headers)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_submit_result_twice(self):
        req = LabTestRequest.objects.create(
            patient=self.patient, requested_by=self.doctor, test_name="CBC",
            assigned_lab_tech=self.lab_tech, status="in_progress",
        )
        LabTestResult.objects.create(request=req, recorded_by=self.lab_tech, result_text="first")
        resp = self.client.post(reverse("labtest-result-create", args=[req.id]),
                                 {"result_text": "second"}, format="json", **self.lab_headers)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_doctor_reviews_result(self):
        req = LabTestRequest.objects.create(
            patient=self.patient, requested_by=self.doctor, test_name="CBC",
            assigned_lab_tech=self.lab_tech, status="completed",
        )
        result = LabTestResult.objects.create(request=req, recorded_by=self.lab_tech, result_text="normal")
        resp = self.client.post(reverse("labtest-result-review", args=[result.id]), **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        result.refresh_from_db()
        self.assertEqual(result.reviewed_by_id, self.doctor.id)
        self.assertIsNotNone(result.reviewed_at)

    def test_other_doctor_cannot_review_result(self):
        req = LabTestRequest.objects.create(
            patient=self.patient, requested_by=self.doctor, test_name="CBC",
            assigned_lab_tech=self.lab_tech, status="completed",
        )
        result = LabTestResult.objects.create(request=req, recorded_by=self.lab_tech, result_text="normal")
        resp = self.client.post(reverse("labtest-result-review", args=[result.id]), **self.other_doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_doctor_cancels_own_request(self):
        req = LabTestRequest.objects.create(patient=self.patient, requested_by=self.doctor, test_name="CBC")
        resp = self.client.post(reverse("labtest-request-cancel", args=[req.id]), **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        req.refresh_from_db()
        self.assertEqual(req.status, "cancelled")

    def test_patient_has_no_access(self):
        patient_user = make_patient_user()
        self.patient.user = patient_user
        self.patient.save(update_fields=["user"])
        req = LabTestRequest.objects.create(patient=self.patient, requested_by=self.doctor, test_name="CBC")
        resp = self.client.get(reverse("labtest-request-list-create"), **auth_headers(patient_user))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
