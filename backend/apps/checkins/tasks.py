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


@shared_task
def flag_missing_daily_checkins():
    """Missing-check-in monitor (Member 3 / P1).

    Finds every linked patient (has a redeemed `user` account, so they're
    actually able to submit check-ins) who has NOT submitted a `DailyCheckin`
    for today, and raises one in-app doctor-facing Notification per patient
    per day so the gap is visible on the dashboard.

    Deliberately does NOT touch DailyCheckin.ai_risk_level / ai_risk_score in
    any way, and does not create a DailyCheckin row - a missing check-in is
    a missing check-in, not a risk verdict. There is nothing to "fail" into
    here: if a patient has no check-in, this task simply has nothing to read
    a risk from, and never invents one (fail-closed by construction, not by
    a try/except around a risk calculation).

    Reuses the existing apps.notifications.services.create_notification
    in-app notification path (the same one apps.medications.tasks and
    apps.alerts.tasks already use) instead of adding any new model/field -
    see database/BACKEND_RECONCILIATION.md and the Member 3 plan note on not
    blindly adding a schema change for "awaiting data".
    """
    from apps.notifications.models import Notification
    from apps.notifications.services import create_notification
    from apps.patients.models import Patient

    from .models import DailyCheckin

    today = timezone.localdate()

    # Only linked patients are expected to check in - an unredeemed invite
    # (user is null) has no one able to submit one yet.
    expected_patients = Patient.objects.filter(user__isnull=False).select_related("doctor__user")

    checked_in_patient_ids = set(
        DailyCheckin.objects.filter(checkin_date=today).values_list("patient_id", flat=True)
    )

    flagged = 0
    skipped_no_doctor = 0
    already_flagged_today = 0

    for patient in expected_patients:
        if patient.id in checked_in_patient_ids:
            continue

        doctor_user = getattr(patient.doctor, "user", None)
        if doctor_user is None:
            # Data integrity edge case (Patient.doctor is required/RESTRICT in
            # the schema, so this shouldn't normally happen) - skip rather
            # than guess who to notify.
            skipped_no_doctor += 1
            continue

        # Idempotency: this task may run more than once (retries, manual
        # trigger) - don't spam a second "awaiting data" notification for
        # the same patient on the same day.
        already_notified = Notification.objects.filter(
            user=doctor_user,
            related_object_type="missing_checkin",
            related_object_id=patient.id,
            created_at__date=today,
        ).exists()
        if already_notified:
            already_flagged_today += 1
            continue

        create_notification(
            user=doctor_user,
            notification_type=Notification.NotificationType.GENERAL,
            title=f"Missing daily check-in: {patient.name}",
            body=(
                f"{patient.name} has not submitted a daily check-in for {today}. "
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
