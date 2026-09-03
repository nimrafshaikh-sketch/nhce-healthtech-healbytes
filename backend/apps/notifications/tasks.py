from celery import shared_task


@shared_task
def send_caretaker_checkin_email_task(checkin_id):
    from apps.checkins.models import DailyCheckin

    from .services import send_caretaker_checkin_email

    try:
        checkin = DailyCheckin.objects.select_related("patient").get(id=checkin_id)
    except DailyCheckin.DoesNotExist:
        return {"error": "checkin not found"}

    log = send_caretaker_checkin_email(checkin)
    if log is None:
        return {"sent": False, "reason": "no caretaker_email on file"}
    return {"sent": log.sent, "log_id": log.id}


@shared_task
def send_patient_checkin_result_email_task(checkin_id):
    from apps.checkins.models import DailyCheckin

    from .services import send_patient_checkin_result_email

    try:
        checkin = DailyCheckin.objects.select_related("patient__user").get(id=checkin_id)
    except DailyCheckin.DoesNotExist:
        return {"error": "checkin not found"}

    log = send_patient_checkin_result_email(checkin)
    if log is None:
        return {"sent": False, "reason": "patient has no linked account/email"}
    return {"sent": log.sent, "log_id": log.id}


@shared_task
def send_doctor_alert_email_task(alert_id):
    from apps.alerts.models import Alert

    from .services import send_doctor_alert_email

    try:
        alert = Alert.objects.select_related("patient__doctor").get(id=alert_id)
    except Alert.DoesNotExist:
        return {"error": "alert not found"}

    log = send_doctor_alert_email(alert)
    if log is None:
        return {"sent": False, "reason": "doctor has no email on file"}
    return {"sent": log.sent, "log_id": log.id}


@shared_task
def send_patient_medication_reminder_email_task(medication_id):
    from apps.medications.models import Medication

    from .services import send_patient_medication_reminder_email

    try:
        medication = Medication.objects.select_related("patient__user").get(id=medication_id)
    except Medication.DoesNotExist:
        return {"error": "medication not found"}

    log = send_patient_medication_reminder_email(medication)
    if log is None:
        return {"sent": False, "reason": "patient has no linked account/email"}
    return {"sent": log.sent, "log_id": log.id}
