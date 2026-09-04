from django.core import mail
from django.test import TestCase

from apps.checkins.models import DailyCheckin
from apps.core.test_utils import make_doctor, make_patient_user
from apps.notifications.models import EmailNotificationLog
from apps.notifications.services import send_caretaker_checkin_email
from apps.patients.models import Patient


class CaretakerEmailTests(TestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.patient_user = make_patient_user()

    def _make_checkin(self, risk_level, caretaker_email="care@example.com"):
        patient = Patient.objects.create(
            doctor=self.doctor.doctor_profile, name="Ivy", user=self.patient_user,
            caretaker_name="Carl", caretaker_email=caretaker_email,
        , date_of_birth="1990-01-01")
        return DailyCheckin.objects.create(
            patient=patient, checkin_date="2026-01-01", ai_risk_level=risk_level,
        )

    def test_low_risk_sends_email(self):
        checkin = self._make_checkin("low")
        log = send_caretaker_checkin_email(checkin)
        self.assertIsNotNone(log)
        self.assertTrue(log.sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["care@example.com"])

    def test_medium_risk_sends_email(self):
        checkin = self._make_checkin("medium")
        log = send_caretaker_checkin_email(checkin)
        self.assertTrue(log.sent)
        self.assertEqual(len(mail.outbox), 1)

    def test_no_caretaker_email_on_file_is_noop(self):
        checkin = self._make_checkin("low", caretaker_email="")
        log = send_caretaker_checkin_email(checkin)
        self.assertIsNone(log)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(EmailNotificationLog.objects.count(), 0)
