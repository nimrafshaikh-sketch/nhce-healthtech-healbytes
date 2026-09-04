from celery import shared_task


@shared_task
def route_alert_for_checkin(checkin_id):
    """Creates (or skips) an Alert for a check-in based on apps.alerts.rules,
    fans out an in-app Notification to the doctor, and - for HIGH severity
    only (apps.alerts.rules.should_email_doctor) - also emails the doctor.
    Caretaker email for non-urgent risk levels is handled separately, from
    apps.checkins.tasks.process_checkin_ai_analysis.
    """
    from apps.checkins.models import DailyCheckin

    from .models import Alert
    from .rules import determine_alert_for_checkin

    try:
        checkin = DailyCheckin.objects.select_related("patient__doctor").get(id=checkin_id)
    except DailyCheckin.DoesNotExist:
        return {"error": "checkin not found"}

    decision = determine_alert_for_checkin(checkin)
    if decision is None:
        return {"alert_created": False, "risk_level": checkin.ai_risk_level}

    # Idempotency guard: if this task is retried or otherwise runs twice for
    # the same checkin (e.g. a Celery retry after a transient failure, or a
    # duplicate task dispatch), do not create a second Alert or send a second
    # doctor email for it. One checkin -> at most one Alert.
    existing_alert = Alert.objects.filter(checkin_id=checkin_id).first()
    if existing_alert is not None:
        return {
            "alert_created": False,
            "reason": "duplicate: an alert already exists for this checkin",
            "alert_id": existing_alert.id,
        }

    severity, recipient_role, reason = decision
    alert = Alert.objects.create(
        patient=checkin.patient,
        checkin=checkin,
        severity=severity,
        recipient_role=recipient_role,
        reason=reason,
    )

    from apps.notifications.services import create_notification

    if recipient_role in (Alert.RecipientRole.DOCTOR, Alert.RecipientRole.DOCTOR_AND_CARETAKER):
        doctor_user = getattr(checkin.patient, "doctor", None)
        if doctor_user:
            create_notification(
                user=doctor_user,
                notification_type="alert",
                title=f"Alert: {checkin.patient.full_name} ({severity})",
                body=reason,
                related_object_type="alert",
                related_object_id=alert.id,
            )
    # Caretaker has no login/User account in this backend's scope (no
    # caretaker auth was requested) - caretaker delivery for HIGH severity is
    # DB-only via the Alert record itself, visible through /api/alerts/.
    # (Low/medium caretaker email is handled separately - see
    # apps.checkins.tasks.process_checkin_ai_analysis.)

    from .rules import should_email_doctor
    if should_email_doctor(severity):
        from apps.notifications.tasks import send_doctor_alert_email_task
        send_doctor_alert_email_task.delay(alert.id)

    return {"alert_created": True, "alert_id": alert.id, "recipient_role": recipient_role}
