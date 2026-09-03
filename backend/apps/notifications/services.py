"""Email-sending services for the notification system.

All actual SMTP delivery goes through Django's configured EMAIL_BACKEND
(console backend by default - see settings/.env.example; swap to real SMTP
via env vars only, no code changes needed here). Every send attempt -
success or failure - is logged via EmailNotificationLog for auditability.

These functions do the synchronous work; the Celery tasks in
apps.notifications.tasks wrap them for async dispatch.
"""
from django.conf import settings
from django.core.mail import send_mail

from .models import EmailNotificationLog, Notification


def create_notification(*, user, notification_type, title, body="", related_object_type="", related_object_id=None):
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        body=body,
        related_object_type=related_object_type,
        related_object_id=related_object_id,
    )


def _send_and_log(*, recipient_type, recipient_user, recipient_email, category, patient,
                   subject, body, checkin=None, alert=None, medication=None, risk_level=""):
    log = EmailNotificationLog.objects.create(
        recipient_type=recipient_type, recipient_user=recipient_user, recipient_email=recipient_email,
        category=category, patient=patient, checkin=checkin, alert=alert, medication=medication,
        subject=subject, risk_level=risk_level,
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient_email], fail_silently=False)
        log.sent = True
        log.save(update_fields=["sent"])
    except Exception as exc:  # noqa: BLE001 - log and move on, never break the caller's flow
        log.error = str(exc)
        log.save(update_fields=["error"])
    return log


def send_caretaker_checkin_email(checkin):
    """"Not too serious" (low/medium risk) check-in summary emailed to the
    patient's caretaker, if one is on file. See apps.alerts.rules.should_email_caretaker.
    """
    patient = checkin.patient
    if not patient.caretaker_email:
        return None

    subject = f"Check-in update for {patient.name}"
    greeting_name = patient.caretaker_name or "there"
    symptoms_text = ", ".join(checkin.symptoms) if checkin.symptoms else "none reported"
    body = "\n".join([
        f"Hi {greeting_name},",
        "",
        f"{patient.name} submitted a daily check-in on {checkin.checkin_date} "
        f"with a '{checkin.ai_risk_level}' risk assessment - nothing urgent, just keeping you informed.",
        "",
        f"Symptoms: {symptoms_text}",
        f"Notes: {checkin.notes or '-'}",
        "",
        "This is an automated message from HealBytes.",
    ])
    return _send_and_log(
        recipient_type=EmailNotificationLog.RecipientType.CARETAKER,
        recipient_user=None, recipient_email=patient.caretaker_email,
        category=EmailNotificationLog.Category.CARETAKER_UPDATE, patient=patient,
        subject=subject, body=body, checkin=checkin, risk_level=checkin.ai_risk_level,
    )


def send_patient_checkin_result_email(checkin):
    """Emails the patient their own AI risk result (reason + recommended
    action) after a check-in. See apps.alerts.rules.should_email_patient_result.
    """
    patient = checkin.patient
    if not patient.user_id or not patient.user.email:
        return None

    subject = f"Your check-in result for {checkin.checkin_date}"
    body = "\n".join([
        f"Hi {patient.name},",
        "",
        f"Your check-in on {checkin.checkin_date} was assessed as '{checkin.ai_risk_level}' risk.",
        "",
        f"Reason: {checkin.ai_notes or '-'}",
        f"Recommended action: {checkin.ai_recommended_action or '-'}",
        "",
        "This is an automated message from HealBytes. If you feel unwell, please contact your doctor.",
    ])
    return _send_and_log(
        recipient_type=EmailNotificationLog.RecipientType.PATIENT,
        recipient_user=patient.user, recipient_email=patient.user.email,
        category=EmailNotificationLog.Category.CHECKIN_RESULT, patient=patient,
        subject=subject, body=body, checkin=checkin, risk_level=checkin.ai_risk_level,
    )


def send_doctor_alert_email(alert):
    """Emails the doctor for a HIGH-severity alert only (see
    apps.alerts.rules.should_email_doctor) - medium/low stay dashboard/API-only
    so the doctor isn't flooded with email for every moderate case.
    """
    patient = alert.patient
    doctor = patient.doctor
    if not doctor or not doctor.user.email:
        return None

    subject = f"[HealBytes] {alert.risk_level} alert - {patient.name}"
    body = "\n".join([
        f"Hi Dr. {doctor.user.name or doctor.user.email},",
        "",
        f"A {alert.risk_level} alert was raised for {patient.name}.",
        "",
        f"Reason: {alert.reason}",
        "",
        "Please review this patient's check-in history and respond as appropriate.",
        "This is an automated message from HealBytes.",
    ])
    log = _send_and_log(
        recipient_type=EmailNotificationLog.RecipientType.DOCTOR,
        recipient_user=doctor.user, recipient_email=doctor.user.email,
        category=EmailNotificationLog.Category.ALERT, patient=patient,
        subject=subject, body=body, checkin=alert.checkin, alert=alert, risk_level=alert.risk_level,
    )

    return log


def send_patient_medication_reminder_email(medication):
    """Emails the patient a reminder for a due medication, alongside the
    existing in-app Notification created in apps.medications.tasks.
    """
    patient = medication.patient
    if not patient.user_id or not patient.user.email:
        return None

    subject = f"Reminder: take {medication.name}"
    body = "\n".join([
        f"Hi {patient.name},",
        "",
        f"This is a reminder to take {medication.name} ({medication.dosage}).",
        f"Instructions: {medication.instructions or 'as prescribed'}",
        "",
        "This is an automated message from HealBytes.",
    ])
    return _send_and_log(
        recipient_type=EmailNotificationLog.RecipientType.PATIENT,
        recipient_user=patient.user, recipient_email=patient.user.email,
        category=EmailNotificationLog.Category.MEDICATION_REMINDER, patient=patient,
        subject=subject, body=body, medication=medication,
    )
