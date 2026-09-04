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

    Finds every linked, active patient who has NOT submitted a DailyCheckin
    for today, and raises:
      - one in-app doctor-facing "awaiting data" Notification per patient per
        day (existing behavior, unchanged - never a risk level, see below), and
      - one in-app patient-facing follow-up reminder Notification per patient
        per day (Feature: patient follow-up reminder), so the patient sees a
        simple nudge to submit their check-in.

    Both reuse the existing Notification model and its GENERAL type - no new
    notification system, model, or type is introduced. A missing check-in is
    NEVER converted into a risk level or into an Alert/HIGH-risk email: this
    task never touches DailyCheckin.ai_risk_level, never calls the AI risk
    engine, and never creates an Alert - it only raises in-app "awaiting
    data" notices. Once a patient submits today's check-in, they drop out of
    `expected_patients - checked_in_patient_ids` on the next run, so nothing
    needs to be explicitly "cleared" - the overdue condition simply stops
    being reported.
    """
    from apps.notifications.models import Notification
    from apps.notifications.services import create_notification
    from apps.patients.models import Patient

    from .models import DailyCheckin

    today = timezone.localdate()

    # is_active=True excludes discharged/inactive patients - see Patient.is_active.
    expected_patients = Patient.objects.filter(
        user__isnull=False, is_active=True,
    ).select_related("doctor", "user")

    checked_in_patient_ids = set(
        DailyCheckin.objects.filter(checkin_date=today).values_list("patient_id", flat=True)
    )

    flagged = 0
    skipped_no_doctor = 0
    already_flagged_today = 0
    patient_reminders_sent = 0
    patient_reminders_already_sent_today = 0

    for patient in expected_patients:
        if patient.id in checked_in_patient_ids:
            continue

        p_name = getattr(patient, "full_name", None) or getattr(patient, "name", "Patient")

        # --- Doctor-facing "awaiting data" notification (existing behavior, unchanged) ---
        doctor_user = getattr(patient.doctor, "user", patient.doctor)
        if doctor_user is None:
            skipped_no_doctor += 1
        else:
            already_notified = Notification.objects.filter(
                user=doctor_user,
                related_object_type="missing_checkin",
                related_object_id=patient.id,
                created_at__date=today,
            ).exists()
            if already_notified:
                already_flagged_today += 1
            else:
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

        # --- Patient-facing follow-up reminder (Feature: patient follow-up
        # reminder). Deliberately a distinct related_object_type from the
        # doctor notification above, so the two dedupe independently and
        # neither can mask the other. In-app only, matching the existing
        # Notification model - no new email/SMS provider is introduced here. ---
        if patient.user_id is None:
            continue
        already_reminded = Notification.objects.filter(
            user=patient.user,
            related_object_type="missing_checkin_reminder",
            related_object_id=patient.id,
            created_at__date=today,
        ).exists()
        if already_reminded:
            patient_reminders_already_sent_today += 1
            continue
        create_notification(
            user=patient.user,
            notification_type=Notification.NotificationType.GENERAL,
            title="Daily check-in reminder",
            body="Your daily health check-in is pending. Please submit it when you can.",
            related_object_type="missing_checkin_reminder",
            related_object_id=patient.id,
        )
        patient_reminders_sent += 1

    return {
        "date": str(today),
        "expected_patients": expected_patients.count(),
        "flagged_awaiting_data": flagged,
        "already_flagged_today": already_flagged_today,
        "skipped_no_doctor": skipped_no_doctor,
        "patient_reminders_sent": patient_reminders_sent,
        "patient_reminders_already_sent_today": patient_reminders_already_sent_today,
    }
