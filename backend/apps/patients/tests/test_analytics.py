from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.checkins.models import DailyCheckin
from apps.core.test_utils import make_doctor, make_lab_tech
from apps.labtests.models import LabTestRequest, LabTestResult
from apps.patients.analytics_views import _build_analytics
from apps.patients.models import Patient


class BuildAnalyticsExtensionTests(TestCase):
    """Member 3 / P1: analytics extension.

    Covers the three additions to _build_analytics - most_recent_lab_result,
    most_recent_prescription, days_since_last_checkin - plus the "no data"
    edge cases. Existing checkins/medications/alerts aggregate keys are left
    untouched by this work and aren't re-tested here.
    """

    def setUp(self):
        self.doctor = make_doctor()
        self.patient = Patient.objects.create(
            doctor=self.doctor, full_name="Nora", date_of_birth="1990-01-01",
        )

    def test_no_checkins_returns_none_not_zero(self):
        analytics = _build_analytics(self.patient)
        self.assertIsNone(analytics["days_since_last_checkin"])

    def test_days_since_last_checkin_counts_from_most_recent(self):
        DailyCheckin.objects.create(patient=self.patient)  # auto_now_add -> today

        analytics = _build_analytics(self.patient)

        self.assertEqual(analytics["days_since_last_checkin"], 0)

    def test_days_since_last_checkin_yesterday_is_one(self):
        checkin = DailyCheckin.objects.create(patient=self.patient)
        DailyCheckin.objects.filter(pk=checkin.pk).update(
            checkin_date=timezone.localdate() - timedelta(days=1)
        )

        analytics = _build_analytics(self.patient)

        self.assertEqual(analytics["days_since_last_checkin"], 1)

    def test_days_since_last_checkin_uses_the_most_recent_of_several(self):
        older = DailyCheckin.objects.create(patient=self.patient)
        DailyCheckin.objects.filter(pk=older.pk).update(
            checkin_date=timezone.localdate() - timedelta(days=5)
        )

        analytics = _build_analytics(self.patient)

        self.assertEqual(analytics["days_since_last_checkin"], 5)

    def test_no_lab_result_returns_none(self):
        analytics = _build_analytics(self.patient)
        self.assertIsNone(analytics["most_recent_lab_result"])

    def test_most_recent_lab_result_is_returned(self):
        lab_tech = make_lab_tech()
        request = LabTestRequest.objects.create(
            patient=self.patient, requested_by=self.doctor,
            test_name=LabTestRequest.TestName.CBC, status=LabTestRequest.Status.COMPLETED,
        )
        LabTestResult.objects.create(
            request=request, recorded_by=lab_tech, result_text="WBC 7.2, normal range",
        )

        analytics = _build_analytics(self.patient)

        result = analytics["most_recent_lab_result"]
        self.assertIsNotNone(result)
        self.assertEqual(result["test_name"], "Complete Blood Count")
        self.assertEqual(result["status"], LabTestRequest.Status.COMPLETED)
        self.assertEqual(result["result_text"], "WBC 7.2, normal range")
        self.assertIsNone(result["reviewed_at"])

    def test_most_recent_lab_result_picks_the_latest_of_several(self):
        lab_tech = make_lab_tech()
        older_request = LabTestRequest.objects.create(
            patient=self.patient, requested_by=self.doctor, test_name=LabTestRequest.TestName.CBC,
        )
        LabTestResult.objects.create(request=older_request, recorded_by=lab_tech, result_text="older")

        newer_request = LabTestRequest.objects.create(
            patient=self.patient, requested_by=self.doctor, test_name=LabTestRequest.TestName.HBA1C,
        )
        LabTestResult.objects.create(request=newer_request, recorded_by=lab_tech, result_text="newer")

        analytics = _build_analytics(self.patient)

        self.assertEqual(analytics["most_recent_lab_result"]["result_text"], "newer")

    def test_prescription_is_none_when_no_prescriptions(self):
        analytics = _build_analytics(self.patient)

        self.assertIn("most_recent_prescription", analytics)
        self.assertIsNone(analytics["most_recent_prescription"])

    def test_most_recent_prescription_is_returned(self):
        from apps.medications.models import Prescription
        Prescription.objects.create(
            patient=self.patient, doctor=self.doctor,
            medication_name="TestMed", dosage="10mg", frequency="daily", duration="10 days"
        )
        analytics = _build_analytics(self.patient)
        self.assertIsNotNone(analytics["most_recent_prescription"])
        self.assertEqual(analytics["most_recent_prescription"]["medication_name"], "TestMed")

    def test_existing_analytics_shape_preserved(self):
        analytics = _build_analytics(self.patient)

        self.assertIn("checkins", analytics)
        self.assertIn("medications", analytics)
        self.assertIn("alerts", analytics)
        self.assertEqual(analytics["patient_id"], self.patient.id)
