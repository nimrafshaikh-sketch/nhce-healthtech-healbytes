from django.test import TestCase

from apps.checkins.models import DailyCheckin
from apps.checkins.tasks import flag_missing_daily_checkins
from apps.core.test_utils import make_doctor, make_patient_user
from apps.notifications.models import Notification
from apps.patients.models import Patient


class FlagMissingDailyCheckinsTests(TestCase):
    """Member 3 / P1: missing-check-in monitor.

    Core safety property under test: a missing check-in NEVER produces a
    risk level or risk score anywhere - only an in-app "awaiting data"
    notification to the doctor, via the existing notifications pattern.
    """

    def setUp(self):
        self.doctor = make_doctor()

    def _linked_patient(self, name="Frank", **kwargs):
        user = make_patient_user(email=f"{name.lower()}@example.com", username=name.lower())
        return Patient.objects.create(
            doctor=self.doctor.doctor_profile, name=name, date_of_birth="1990-01-01",
            user=user, **kwargs,
        )

    def test_patient_without_checkin_is_flagged_as_awaiting_data(self):
        patient = self._linked_patient("Frank")

        result = flag_missing_daily_checkins()

        self.assertEqual(result["flagged_awaiting_data"], 1)
        notification = Notification.objects.get(
            user=self.doctor, related_object_type="missing_checkin", related_object_id=patient.id,
        )
        self.assertIn("Frank", notification.title)
        self.assertIn("awaiting data", notification.body)

    def test_patient_who_already_checked_in_today_is_not_flagged(self):
        patient = self._linked_patient("Grace")
        DailyCheckin.objects.create(patient=patient)  # checkin_date is auto_now_add -> today

        result = flag_missing_daily_checkins()

        self.assertEqual(result["flagged_awaiting_data"], 0)
        self.assertFalse(
            Notification.objects.filter(related_object_type="missing_checkin", related_object_id=patient.id).exists()
        )

    def test_unlinked_patient_draft_is_not_flagged(self):
        # No `user` yet -> invitation not redeemed -> nobody is able to check in.
        Patient.objects.create(doctor=self.doctor.doctor_profile, name="Draft", date_of_birth="1990-01-01")

        result = flag_missing_daily_checkins()

        self.assertEqual(result["flagged_awaiting_data"], 0)
        self.assertEqual(result["expected_patients"], 0)

    def test_running_twice_in_one_day_does_not_duplicate_notification(self):
        self._linked_patient("Hank")

        flag_missing_daily_checkins()
        second_result = flag_missing_daily_checkins()

        self.assertEqual(second_result["flagged_awaiting_data"], 0)
        self.assertEqual(second_result["already_flagged_today"], 1)
        self.assertEqual(Notification.objects.filter(related_object_type="missing_checkin").count(), 1)

    def test_missing_checkin_never_creates_a_daily_checkin_or_risk_value(self):
        patient = self._linked_patient("Ivy")

        flag_missing_daily_checkins()

        # No DailyCheckin row was fabricated for the missing day, and
        # therefore no ai_risk_level/ai_risk_score exists to inspect - the
        # monitor has nothing to assign a risk to, by construction.
        self.assertFalse(DailyCheckin.objects.filter(patient=patient).exists())

    def test_notification_uses_general_type_not_a_new_choice(self):
        # No schema change was made to Notification.NotificationType -
        # confirms the monitor stayed within the existing model.
        self._linked_patient("Jack")

        flag_missing_daily_checkins()

        notification = Notification.objects.get(related_object_type="missing_checkin")
        self.assertEqual(notification.notification_type, Notification.NotificationType.GENERAL)
