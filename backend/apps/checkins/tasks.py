from celery import shared_task
from django.utils import timezone


@shared_task
def process_checkin_ai_analysis(checkin_id):
    """Sends a check-in to the AI engine, stores the risk verdict
    (riskLevel/riskScore/reason/recommendedAction), then hands off to:
      - apps.alerts to route a doctor-facing Alert per the business rules
      - apps.notifications to email the caretaker (low/medium) and the
        patient their own risk result (low/medium/high)
    """
    from .ai_client import analyze_checkin
    from .models import DailyCheckin

    try:
        checkin = DailyCheckin.objects.select_related("patient").get(id=checkin_id)
    except DailyCheckin.DoesNotExist:
        return {"error": "checkin not found"}

    result = analyze_checkin(checkin)
    checkin.ai_risk_level = result["risk_level"]
    checkin.ai_risk_score = result.get("risk_score")
    checkin.ai_notes = result.get("reason", "")
    checkin.ai_recommended_action = result.get("recommended_action", "")
    checkin.ai_notification_recipient = result.get("notification_recipient", "")
    checkin.ai_processed_at = timezone.now()
    checkin.save(update_fields=[
        "ai_risk_level", "ai_risk_score", "ai_notes", "ai_recommended_action",
        "ai_notification_recipient", "ai_processed_at",
    ])

    from apps.alerts.tasks import route_alert_for_checkin
    route_alert_for_checkin.delay(checkin.id)

    from apps.alerts.rules import should_email_caretaker, should_email_patient_result
    if should_email_caretaker(checkin.ai_risk_level) and checkin.patient.caretaker_email:
        from apps.notifications.tasks import send_caretaker_checkin_email_task
        send_caretaker_checkin_email_task.delay(checkin.id)

    if should_email_patient_result(checkin.ai_risk_level) and checkin.patient.user_id:
        from apps.notifications.tasks import send_patient_checkin_result_email_task
        send_patient_checkin_result_email_task.delay(checkin.id)

    return {"checkin_id": checkin.id, "risk_level": checkin.ai_risk_level}


@shared_task
def flag_missing_daily_checkins():
    """Missing-check-in monitor.

    Finds every linked patient who has NOT submitted a DailyCheckin for today,
    and raises one in-app doctor-facing Notification per patient per day.
    """
    from apps.notifications.models import Notification
    from apps.notifications.services import create_notification
    from apps.patients.models import Patient

    from .models import DailyCheckin

    today = timezone.localdate()

    expected_patients = Patient.objects.filter(user__isnull=False).select_related("doctor")

    checked_in_patient_ids = set(
        DailyCheckin.objects.filter(checkin_date=today).values_list("patient_id", flat=True)
    )

    flagged = 0
    skipped_no_doctor = 0
    already_flagged_today = 0

    for patient in expected_patients:
        if patient.id in checked_in_patient_ids:
            continue

        doctor_user = getattr(patient.doctor, "user", patient.doctor)
        if doctor_user is None:
            skipped_no_doctor += 1
            continue

        already_notified = Notification.objects.filter(
            user=doctor_user,
            related_object_type="missing_checkin",
            related_object_id=patient.id,
            created_at__date=today,
        ).exists()
        if already_notified:
            already_flagged_today += 1
            continue

        p_name = getattr(patient, "full_name", None) or getattr(patient, "name", "Patient")
        create_notification(
            user=doctor_user,
            notification_type=Notification.NotificationType.GENERAL,
            title=f"Missing daily check-in: {p_name}",
            body=(
                f"{p_name} has not submitted a daily check-in for {today}. "
                "No risk assessment is available for today - patient status is "
                "awaiting data, not a risk level."
            ),
            related_object_type="missing_checkin",
            related_object_id=patient.id,
        )
        flagged += 1

    return {
        "date": str(today),
        "expected_patients": expected_patients.count(),
        "flagged_awaiting_data": flagged,
        "already_flagged_today": already_flagged_today,
        "skipped_no_doctor": skipped_no_doctor,
    }
