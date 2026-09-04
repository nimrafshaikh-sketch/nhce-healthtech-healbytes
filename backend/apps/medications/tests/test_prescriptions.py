from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.core.test_utils import auth_headers, make_doctor, make_patient_user, make_receptionist, make_lab_tech
from apps.patients.models import Patient
from apps.medications.models import Prescription
from apps.qr.models import QRAccessGrant


class PrescriptionTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.patient_user = make_patient_user()
        self.patient = Patient.objects.create(doctor=self.doctor, full_name="Hank Test", user=self.patient_user)
        self.doctor_headers = auth_headers(self.doctor)
        self.patient_headers = auth_headers(self.patient_user)

    def test_doctor_can_create_prescription_for_assigned_patient(self):
        data = {
            "patient": self.patient.id,
            "medication_name": "Lisinopril",
            "dosage": "10mg",
            "frequency": "Once daily",
            "duration": "30 days",
            "instructions": "Take in the morning"
        }
        resp = self.client.post(reverse("prescription-list-create"), data, format="json", **self.doctor_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Prescription.objects.count(), 1)
        self.assertEqual(resp.data["doctor"], self.doctor.id)

    def test_doctor_cannot_create_prescription_for_unassigned_patient(self):
        other_doctor = make_doctor(email="other@example.com", username="other")
        data = {
            "patient": self.patient.id,
            "medication_name": "Lisinopril",
            "dosage": "10mg",
            "frequency": "Once daily",
            "duration": "30 days",
            "instructions": "Take in the morning"
        }
        resp = self.client.post(reverse("prescription-list-create"), data, format="json", **auth_headers(other_doctor))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_with_active_qr_grant_can_create_prescription(self):
        other_doctor = make_doctor(email="other@example.com", username="other")
        QRAccessGrant.grant(patient=self.patient, doctor=other_doctor)
        
        data = {
            "patient": self.patient.id,
            "medication_name": "Lisinopril",
            "dosage": "10mg",
            "frequency": "Once daily",
            "duration": "30 days",
            "instructions": "Take in the morning"
        }
        resp = self.client.post(reverse("prescription-list-create"), data, format="json", **auth_headers(other_doctor))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_patient_can_view_own_prescriptions(self):
        Prescription.objects.create(patient=self.patient, doctor=self.doctor, medication_name="TestMed", dosage="5mg", frequency="daily", duration="10 days")
        resp = self.client.get(reverse("prescription-list-create"), **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["results"]), 1)

    def test_patient_cannot_create_prescription(self):
        data = {
            "patient": self.patient.id,
            "medication_name": "TestMed",
            "dosage": "10mg",
            "frequency": "daily",
            "duration": "10 days"
        }
        resp = self.client.post(reverse("prescription-list-create"), data, format="json", **self.patient_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_receptionist_cannot_view_prescriptions(self):
        rec = make_receptionist()
        resp = self.client.get(reverse("prescription-list-create"), **auth_headers(rec))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["results"]), 0)  # Receptionist sees nothing

    def test_lab_tech_cannot_view_prescriptions(self):
        lt = make_lab_tech()
        resp = self.client.get(reverse("prescription-list-create"), **auth_headers(lt))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["results"]), 0)
