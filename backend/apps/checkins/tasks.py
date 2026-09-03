from celery import shared_task
from django.utils import timezone


@shared_task
def process_checkin_ai_analysis(checkin_id):
    """Sends a check-in to the AI engine (stub), stores the risk verdict
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
