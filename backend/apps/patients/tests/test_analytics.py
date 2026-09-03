from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.checkins.models import DailyCheckin
from apps.core.test_utils import make_doctor
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
            doctor=self.doctor.doctor_profile, name="Nora", date_of_birth="1990-01-01",
        )

    def test_no_checkins_returns_none_not_zero(self):
        analytics = _build_analytics(self.patient)
        self.assertIsNone(analytics["days_since_last_checkin"])

    def test_days_since_last_checkin_counts_from_most_recent(self):
        DailyCheckin.objects.create(patient=self.patient)  # auto_now_add -> today

        analytics = _build_analytics(self.patient)

        self.assertEqual(analytics["days_since_last_checkin"], 0)

    def test_days_since_last_checkin_uses_the_most_recent_of_several(self):
        older = DailyCheckin.objects.create(patient=self.patient)
        DailyCheckin.objects.filter(pk=older.pk).update(
            checkin_date=timezone.localdate() - timedelta(days=5)
        )

        analytics = _build_analytics(self.patient)

        self.assertEqual(analytics["days_since_last_checkin"], 5)

    def test_lab_result_and_prescription_are_stubbed_none_pending_member2_models(self):
        # LabResult / Prescription don't exist as Django models yet - the
        # keys must still be present (stable shape for Member 4) with an
        # honest None rather than a fabricated value.
        analytics = _build_analytics(self.patient)

        self.assertIn("most_recent_lab_result", analytics)
        self.assertIn("most_recent_prescription", analytics)
        self.assertIsNone(analytics["most_recent_lab_result"])
        self.assertIsNone(analytics["most_recent_prescription"])

    def test_existing_analytics_shape_preserved(self):
        analytics = _build_analytics(self.patient)

        self.assertIn("checkins", analytics)
        self.assertIn("medications", analytics)
        self.assertIn("alerts", analytics)
        self.assertEqual(analytics["patient_id"], self.patient.id)
