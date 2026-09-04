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
            doctor=self.doctor, full_name=name, date_of_birth="1990-01-01",
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
        Patient.objects.create(doctor=self.doctor, full_name="Draft", date_of_birth="1990-01-01")

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

    def test_inactive_patient_is_not_flagged_or_reminded(self):
        patient = self._linked_patient("Kim", is_active=False)

        result = flag_missing_daily_checkins()

        self.assertEqual(result["expected_patients"], 0)
        self.assertFalse(
            Notification.objects.filter(related_object_type__startswith="missing_checkin").exists()
        )

    def test_missing_checkin_never_creates_an_alert_or_sends_doctor_email(self):
        # Explicit safety-contract check: the monitor must never escalate a
        # missing check-in into an Alert or the HIGH-risk SMTP path -
        # those are owned entirely by apps.alerts / apps.notifications and
        # only ever triggered by an actual AI risk verdict on a submitted
        # check-in (see apps.checkins.tasks.process_checkin_ai_analysis).
        from django.core import mail

        from apps.alerts.models import Alert

        self._linked_patient("Liam")

        flag_missing_daily_checkins()

        self.assertEqual(Alert.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)


class PatientFollowUpReminderTests(TestCase):
    """Feature: patient follow-up reminder - the monitor also notifies the
    PATIENT (not just the doctor) that their check-in is pending, using the
    same existing Notification model/GENERAL type, deduplicated per patient
    per day independently of the doctor-facing notification.
    """

    def setUp(self):
        self.doctor = make_doctor()

    def _linked_patient(self, name="Mona", **kwargs):
        user = make_patient_user(email=f"{name.lower()}@example.com", username=name.lower())
        return Patient.objects.create(
            doctor=self.doctor, full_name=name, date_of_birth="1990-01-01",
            user=user, **kwargs,
        )

    def test_patient_receives_pending_checkin_reminder(self):
        patient = self._linked_patient("Mona")

        result = flag_missing_daily_checkins()

        self.assertEqual(result["patient_reminders_sent"], 1)
        reminder = Notification.objects.get(
            user=patient.user, related_object_type="missing_checkin_reminder", related_object_id=patient.id,
        )
        self.assertEqual(reminder.notification_type, Notification.NotificationType.GENERAL)
        self.assertIn("pending", reminder.body)
        # No sensitive medical info in the reminder - just a simple nudge.
        self.assertNotIn("risk", reminder.body.lower())

    def test_patient_with_todays_checkin_receives_no_reminder(self):
        patient = self._linked_patient("Nina")
        DailyCheckin.objects.create(patient=patient)  # today

        flag_missing_daily_checkins()

        self.assertFalse(
            Notification.objects.filter(
                user=patient.user, related_object_type="missing_checkin_reminder",
            ).exists()
        )

    def test_running_twice_in_one_day_does_not_duplicate_patient_reminder(self):
        self._linked_patient("Omar")

        flag_missing_daily_checkins()
        second_result = flag_missing_daily_checkins()

        self.assertEqual(second_result["patient_reminders_sent"], 0)
        self.assertEqual(second_result["patient_reminders_already_sent_today"], 1)
        self.assertEqual(
            Notification.objects.filter(related_object_type="missing_checkin_reminder").count(), 1
        )

    def test_reminder_condition_clears_once_patient_checks_in(self):
        patient = self._linked_patient("Priya")

        first = flag_missing_daily_checkins()
        self.assertEqual(first["patient_reminders_sent"], 1)

        # Patient submits today's check-in in between monitor runs.
        DailyCheckin.objects.create(patient=patient)

        second = flag_missing_daily_checkins()

        self.assertEqual(second["patient_reminders_sent"], 0)
        self.assertEqual(second["patient_reminders_already_sent_today"], 0)
        # Still exactly the one reminder from the first run - not re-flagged,
        # not duplicated.
        self.assertEqual(
            Notification.objects.filter(related_object_type="missing_checkin_reminder").count(), 1
        )

    def test_doctor_and_patient_reminders_dedupe_independently(self):
        # Reusing the doctor's own account as a degenerate edge case would be
        # unusual; this test instead confirms the two notification rows are
        # genuinely independent by checking both exist after one run and
        # neither's dedupe check accidentally matches the other's row.
        patient = self._linked_patient("Quinn")

        flag_missing_daily_checkins()

        self.assertTrue(
            Notification.objects.filter(user=self.doctor, related_object_type="missing_checkin").exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=patient.user, related_object_type="missing_checkin_reminder",
            ).exists()
        )
