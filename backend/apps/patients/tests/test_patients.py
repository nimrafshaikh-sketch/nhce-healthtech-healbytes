from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor, make_lab_tech, make_receptionist, make_patient_user
from apps.patients.models import Patient


class PatientApiTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.other_doctor = make_doctor(email="other@example.com", username="other")
        self.headers = auth_headers(self.doctor)

    def test_doctor_can_add_and_list_own_patients(self):
        resp = self.client.post(reverse("patient-list-create"), {"full_name": "Carol"}, format="json", **self.headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        resp = self.client.get(reverse("patient-list-create"), **self.headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

    def test_doctor_cannot_see_other_doctors_patients(self):
        Patient.objects.create(doctor=self.other_doctor, full_name="NotMine")
        resp = self.client.get(reverse("patient-list-create"), **self.headers)
        self.assertEqual(resp.data["count"], 0)

    def test_doctor_cannot_access_other_doctors_patient_detail(self):
        p = Patient.objects.create(doctor=self.other_doctor, full_name="NotMine")
        resp = self.client.get(reverse("patient-detail", args=[p.id]), **self.headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_can_search_own_patients_by_name(self):
        Patient.objects.create(doctor=self.doctor, full_name="Priya Shah", phone_number="1112223333")
        Patient.objects.create(doctor=self.doctor, full_name="Amir Khan", phone_number="4445556666")
        resp = self.client.get(reverse("patient-list-create") + "?search=priya", **self.headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["full_name"], "Priya Shah")

    def test_doctor_can_search_own_patients_by_phone(self):
        Patient.objects.create(doctor=self.doctor, full_name="Priya Shah", phone_number="1112223333")
        resp = self.client.get(reverse("patient-list-create") + "?search=222333", **self.headers)
        self.assertEqual(resp.data["count"], 1)

    def test_search_never_returns_other_doctors_patients(self):
        Patient.objects.create(doctor=self.other_doctor, full_name="Priya Shah")
        resp = self.client.get(reverse("patient-list-create") + "?search=priya", **self.headers)
        self.assertEqual(resp.data["count"], 0)

    def test_search_with_no_match_returns_empty_not_error(self):
        Patient.objects.create(doctor=self.doctor, full_name="Priya Shah")
        resp = self.client.get(reverse("patient-list-create") + "?search=zzznomatch", **self.headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)


class ReceptionistPatientManagementTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.other_doctor = make_doctor(email="other@example.com", username="other")
        self.receptionist = make_receptionist()
        self.reception_headers = auth_headers(self.receptionist)

    def test_receptionist_creates_patient_assigned_to_chosen_doctor(self):
        payload = {"full_name": "Nadia", "doctor": self.doctor.id, "phone_number": "5551234"}
        resp = self.client.post(reverse("patient-list-create"), payload, format="json", **self.reception_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        patient = Patient.objects.get(full_name="Nadia")
        self.assertEqual(patient.doctor_id, self.doctor.id)

    def test_receptionist_create_response_excludes_medical_notes_field_not_writable(self):
        payload = {"full_name": "Omar", "doctor": self.doctor.id, "medical_notes": "should be ignored"}
        resp = self.client.post(reverse("patient-list-create"), payload, format="json", **self.reception_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        patient = Patient.objects.get(full_name="Omar")
        self.assertEqual(patient.medical_notes, "")

    def test_receptionist_cannot_list_all_patients(self):
        Patient.objects.create(doctor=self.doctor, full_name="Someone")
        resp = self.client.get(reverse("patient-list-create"), **self.reception_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_cannot_use_receptionist_create(self):
        patient_user = make_patient_user()
        payload = {"full_name": "X", "doctor": self.doctor.id}
        resp = self.client.post(reverse("patient-list-create"), payload, format="json",
                                 **auth_headers(patient_user))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class PatientSearchTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.receptionist = make_receptionist()
        self.reception_headers = auth_headers(self.receptionist)
        self.patient = Patient.objects.create(
            doctor=self.doctor, full_name="Priya Shah", phone_number="9998887777",
            date_of_birth="1990-05-01", medical_notes="secret clinical notes",
        )

    def test_search_by_phone_number(self):
        resp = self.client.get(reverse("patient-search") + "?phone_number=9998887777", **self.reception_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)
        self.assertNotIn("medical_notes", resp.data["results"][0])

    def test_search_by_name_and_dob(self):
        resp = self.client.get(
            reverse("patient-search") + "?name=Priya&date_of_birth=1990-05-01", **self.reception_headers
        )
        self.assertEqual(resp.data["count"], 1)

    def test_search_by_name_alone_is_rejected(self):
        resp = self.client.get(reverse("patient-search") + "?name=Priya", **self.reception_headers)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_with_no_params_is_rejected(self):
        resp = self.client.get(reverse("patient-search"), **self.reception_headers)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_doctor_cannot_use_receptionist_search(self):
        resp = self.client.get(reverse("patient-search") + "?phone_number=9998887777", **auth_headers(self.doctor))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_lab_tech_cannot_use_receptionist_search(self):
        lab_tech = make_lab_tech()
        resp = self.client.get(reverse("patient-search") + "?phone_number=9998887777", **auth_headers(lab_tech))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
