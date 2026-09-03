from django.test import TestCase

from apps.alerts.rules import (
    determine_alert_for_checkin,
    should_email_caretaker,
    should_email_doctor,
    should_email_patient_result,
)


class FakeCheckin:
    def __init__(self, risk_level, notes="", checkin_date="2026-01-01"):
        self.ai_risk_level = risk_level
        self.ai_notes = notes
        self.checkin_date = checkin_date


class AlertRuleTests(TestCase):
    def test_high_risk_routes_to_doctor_and_caretaker(self):
        result = determine_alert_for_checkin(FakeCheckin("high"))
        self.assertIsNotNone(result)
        severity, recipient, _ = result
        self.assertEqual(severity, "high")
        self.assertEqual(recipient, "doctor_and_caretaker")

    def test_medium_risk_routes_to_doctor_only(self):
        _, recipient, _ = determine_alert_for_checkin(FakeCheckin("medium"))
        self.assertEqual(recipient, "doctor")

    def test_low_risk_no_alert(self):
        self.assertIsNone(determine_alert_for_checkin(FakeCheckin("low")))

    def test_unavailable_no_alert(self):
        self.assertIsNone(determine_alert_for_checkin(FakeCheckin("unavailable")))


class CaretakerEmailRuleTests(TestCase):
    def test_low_and_medium_email_caretaker(self):
        self.assertTrue(should_email_caretaker("low"))
        self.assertTrue(should_email_caretaker("medium"))

    def test_high_and_unavailable_do_not_email_caretaker(self):
        self.assertFalse(should_email_caretaker("high"))
        self.assertFalse(should_email_caretaker("unavailable"))
        self.assertFalse(should_email_caretaker("pending"))


class DoctorEmailRuleTests(TestCase):
    def test_high_emails_doctor(self):
        self.assertTrue(should_email_doctor("high"))

    def test_medium_and_low_do_not_email_doctor(self):
        self.assertFalse(should_email_doctor("medium"))
        self.assertFalse(should_email_doctor("low"))


class PatientResultEmailRuleTests(TestCase):
    def test_low_medium_high_email_patient(self):
        self.assertTrue(should_email_patient_result("low"))
        self.assertTrue(should_email_patient_result("medium"))
        self.assertTrue(should_email_patient_result("high"))

    def test_unavailable_and_pending_do_not_email_patient(self):
        self.assertFalse(should_email_patient_result("unavailable"))
        self.assertFalse(should_email_patient_result("pending"))
