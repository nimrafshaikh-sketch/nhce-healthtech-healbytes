"""Alert routing business rules.

**These are DEFAULTS proposed by the backend dev and approved by the team
lead for this hackathon build — no pre-existing agreed rule set existed.**
Kept in one place, deliberately simple, so they're easy to change later
without touching the Celery task plumbing or models.

Rule (AI risk_level -> who gets alerted):
    high   -> Doctor + Caretaker, in-app Alert only (urgent - no email)
    medium -> Doctor in-app Alert, AND caretaker gets an email (not too serious)
    low    -> no in-app Alert (not urgent enough for the doctor dashboard),
              but caretaker still gets an email (not too serious)
    unavailable / pending -> nothing (no Alert, no caretaker email)

The in-app Alert (doctor-facing) and the caretaker email are deliberately
separate mechanisms - see should_email_caretaker() below - because low
risk never creates an Alert but DOES still email the caretaker.
"""
from apps.alerts.models import Alert

RISK_TO_RECIPIENT = {
    "high": Alert.RecipientRole.DOCTOR_AND_CARETAKER,
    "medium": Alert.RecipientRole.DOCTOR,
}
RISK_TO_SEVERITY = {
    "high": Alert.Severity.HIGH,
    "medium": Alert.Severity.MEDIUM,
}


def determine_alert_for_checkin(checkin):
    """Returns (severity, recipient_role, reason) or None if no alert should be raised."""
    risk = checkin.ai_risk_level
    recipient = RISK_TO_RECIPIENT.get(risk)
    if recipient is None:
        return None
    severity = RISK_TO_SEVERITY[risk]
    reason = (
        f"AI risk assessment: {risk.upper()} for check-in on {checkin.checkin_date}."
        + (f" Notes: {checkin.ai_notes}" if checkin.ai_notes else "")
    )
    return severity, recipient, reason


# Risk levels considered "not too serious" -> caretaker gets an email.
# High is deliberately excluded: that case is urgent and goes to the doctor
# in-app instead (see RISK_TO_RECIPIENT above), not email.
CARETAKER_EMAIL_RISK_LEVELS = {"low", "medium"}


def should_email_caretaker(risk_level: str) -> bool:
    return risk_level in CARETAKER_EMAIL_RISK_LEVELS


# Risk levels for which the PATIENT gets an email summarizing their own
# check-in result. Excludes "unavailable"/"pending" - nothing meaningful to
# report if the AI engine didn't return a verdict.
PATIENT_RESULT_EMAIL_RISK_LEVELS = {"low", "medium", "high"}


def should_email_patient_result(risk_level: str) -> bool:
    return risk_level in PATIENT_RESULT_EMAIL_RISK_LEVELS


# Severities for which the DOCTOR gets an email (on top of the in-app Alert
# that's always created for medium/high - see determine_alert_for_checkin).
# Only "high" emails the doctor; medium stays dashboard/API-only, so the
# doctor isn't inundated with email for every moderate check-in.
DOCTOR_EMAIL_SEVERITIES = {Alert.Severity.HIGH}


def should_email_doctor(severity: str) -> bool:
    return severity in DOCTOR_EMAIL_SEVERITIES
