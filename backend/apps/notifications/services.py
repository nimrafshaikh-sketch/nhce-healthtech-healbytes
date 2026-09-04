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
                   subject, body, checkin=None, alert=None, medication=None,
                   lab_test_request=None, risk_level=""):
    log = EmailNotificationLog.objects.create(
        recipient_type=recipient_type, recipient_user=recipient_user, recipient_email=recipient_email,
        category=category, patient=patient, checkin=checkin, alert=alert, medication=medication,
        lab_test_request=lab_test_request, subject=subject, risk_level=risk_level,
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

    subject = f"Check-in update for {patient.full_name}"
    greeting_name = patient.caretaker_name or "there"
    symptoms_text = ", ".join(checkin.symptoms) if checkin.symptoms else "none reported"
    body = "\n".join([
        f"Hi {greeting_name},",
        "",
        f"{patient.full_name} submitted a daily check-in on {checkin.checkin_date} "
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
        f"Hi {patient.full_name},",
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
    if not doctor or not doctor.email:
        return None

    subject = f"[HealBytes] {alert.get_severity_display()} alert - {patient.full_name}"
    body = "\n".join([
        f"Hi Dr. {doctor.get_full_name() or doctor.email},",
        "",
        f"A {alert.severity} alert was raised for {patient.full_name}.",
        "",
        f"Reason: {alert.reason}",
        "",
        "Please review this patient's check-in history and respond as appropriate.",
        "This is an automated message from HealBytes.",
    ])
    log = _send_and_log(
        recipient_type=EmailNotificationLog.RecipientType.DOCTOR,
        recipient_user=doctor, recipient_email=doctor.email,
        category=EmailNotificationLog.Category.ALERT, patient=patient,
        subject=subject, body=body, checkin=alert.checkin, alert=alert, risk_level=alert.severity,
    )
    alert.email_sent = log.sent
    alert.email_error = log.error
    if log.sent:
        from django.utils import timezone
        alert.email_sent_at = timezone.now()
        alert.save(update_fields=["email_sent", "email_sent_at", "email_error"])
    else:
        alert.save(update_fields=["email_sent", "email_error"])
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
        f"Hi {patient.full_name},",
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


def send_lab_tech_new_request_email(lab_request, lab_tech):
    """Emails one lab technician that a new lab test request is waiting in
    the queue. Called once per active lab technician when a doctor creates
    a LabTestRequest (see apps.labtests.tasks.notify_lab_techs_of_new_request) -
    alongside the in-app Notification/badge, from the same backend event.
    """
    patient = lab_request.patient
    if not lab_tech or not lab_tech.email:
        return None

    requesting_doctor = lab_request.requested_by
    doctor_label = (
        f"Dr. {requesting_doctor.get_full_name() or requesting_doctor.email}"
        if requesting_doctor else "A doctor"
    )
    subject = f"[HealBytes] New lab request: {lab_request.get_test_name_display()} - {patient.full_name}"
    body = "\n".join([
        f"Hi {lab_tech.get_full_name() or lab_tech.email},",
        "",
        f"{doctor_label} requested a {lab_request.get_test_name_display()} for {patient.full_name} "
        f"({lab_request.get_priority_display()} priority).",
        "",
        "Open the Lab Technician dashboard to claim this request.",
        "This is an automated message from HealBytes.",
    ])
    return _send_and_log(
        recipient_type=EmailNotificationLog.RecipientType.LAB_TECH,
        recipient_user=lab_tech, recipient_email=lab_tech.email,
        category=EmailNotificationLog.Category.LAB_TEST_REQUEST, patient=patient,
        subject=subject, body=body, lab_test_request=lab_request,
    )


def send_doctor_lab_result_email(result):
    """Emails the requesting doctor that a lab result is ready, including the
    AI Engine's deterministic reference-range read (see
    apps.labtests.ai_client.analyze_lab_result / apps.labtests.tasks) -
    called once per submitted result, alongside the in-app Notification, from
    the same backend event (see apps.labtests.tasks.analyze_and_store_lab_result).
    """
    lab_request = result.request
    patient = lab_request.patient
    doctor = lab_request.requested_by
    if not doctor or not doctor.email:
        return None

    subject = f"[HealBytes] Lab result ready: {lab_request.get_test_name_display()} - {patient.full_name}"
    ai_lines = []
    if result.ai_status:
        ai_lines = [
            "",
            f"AI reference-range read: {result.ai_status}"
            + (f" ({result.ai_numeric_value}{result.ai_unit}, range {result.ai_reference_range})"
               if result.ai_numeric_value is not None else ""),
            result.ai_explanation or "",
        ]
    body = "\n".join([
        f"Hi Dr. {doctor.get_full_name() or doctor.email},",
        "",
        f"The {lab_request.get_test_name_display()} result for {patient.full_name} is ready.",
        "",
        f"Result: {result.result_text}",
        *ai_lines,
        "",
        "Open the patient's profile to review this result.",
        "This is an automated message from HealBytes.",
    ])
    return _send_and_log(
        recipient_type=EmailNotificationLog.RecipientType.DOCTOR,
        recipient_user=doctor, recipient_email=doctor.email,
        category=EmailNotificationLog.Category.LAB_RESULT_READY, patient=patient,
        subject=subject, body=body, lab_test_request=lab_request,
        risk_level=result.ai_risk_level,
    )
