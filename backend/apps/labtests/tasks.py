from celery import shared_task


@shared_task
def notify_lab_techs_of_new_request(lab_request_id):
    """Fans out the 'new lab test request' alert to every lab technician:
    one in-app Notification (dashboard badge) plus one email each, both
    originating from this single backend event (see the ticket's requirement
    that dashboard + email come from the same event, not two systems).

    Broadcast to every lab_tech account rather than a specific assignee,
    because a LabTestRequest has no assigned lab tech until one claims it
    (LabTestClaimView) - the unclaimed queue is shared, so every lab tech
    needs to see/be alerted about it.
    """
    from apps.accounts.models import User
    from apps.notifications.models import Notification
    from apps.notifications.services import create_notification

    from .models import LabTestRequest

    try:
        lab_request = LabTestRequest.objects.select_related("patient", "requested_by").get(id=lab_request_id)
    except LabTestRequest.DoesNotExist:
        return {"error": "lab test request not found"}

    lab_techs = list(User.objects.filter(role=User.Role.LAB_TECH, is_active=True))

    notified = 0
    for lab_tech in lab_techs:
        create_notification(
            user=lab_tech,
            notification_type=Notification.NotificationType.LAB_TEST_REQUEST,
            title=f"New lab request: {lab_request.get_test_name_display()}",
            body=f"{lab_request.patient.full_name} - {lab_request.get_test_name_display()} "
                 f"({lab_request.get_priority_display()} priority)",
            related_object_type="lab_test_request",
            related_object_id=lab_request.id,
        )
        notified += 1

        from apps.notifications.tasks import send_lab_tech_new_request_email_task
        send_lab_tech_new_request_email_task.delay(lab_request.id, lab_tech.id)

    return {"lab_request_id": lab_request.id, "lab_techs_notified": notified}


@shared_task
def analyze_and_store_lab_result(lab_result_id):
    """Runs right after a lab tech submits a result
    (LabTestResultCreateView.post): calls the AI Engine's deterministic
    reference-range analysis (apps.labtests.ai_client.analyze_lab_result),
    stores the structured read on the LabTestResult, and - only when the
    result isn't a plain NORMAL read - alerts the requesting doctor (one
    in-app Notification + one email, both from this single event, same
    pattern as notify_lab_techs_of_new_request above) so an abnormal result
    doesn't just sit unnoticed until the doctor happens to check.

    Completes the workflow the LabTestRequest.test_name field comment always
    intended: Lab Technician -> result -> AI Engine -> analysis -> stored ->
    Doctor. If the AI Engine is unreachable/unconfigured, the result was
    already saved by the view before this task ever ran - AI analysis is
    additive, never a blocker.
    """
    from apps.notifications.models import Notification
    from apps.notifications.services import create_notification

    from .ai_client import analyze_lab_result
    from .models import LabTestResult

    try:
        result = LabTestResult.objects.select_related("request__patient", "request__requested_by").get(id=lab_result_id)
    except LabTestResult.DoesNotExist:
        return {"error": "lab result not found"}

    analysis = analyze_lab_result(result)

    result.ai_status = analysis["status"]
    result.ai_risk_level = analysis["risk_level"]
    result.ai_numeric_value = analysis["numeric_value"]
    result.ai_unit = analysis["unit"]
    result.ai_reference_range = analysis["reference_range"]
    result.ai_explanation = analysis["explanation"]
    result.save(update_fields=[
        "ai_status", "ai_risk_level", "ai_numeric_value", "ai_unit", "ai_reference_range", "ai_explanation",
    ])

    if analysis["risk_level"] == "unavailable":
        return {"lab_result_id": result.id, "ai_status": "unavailable", "doctor_notified": False}

    lab_request = result.request
    doctor = lab_request.requested_by
    notify_doctor = analysis["status"] in ("ELEVATED", "LOW") or analysis["risk_level"] in ("medium", "high")

    if doctor and notify_doctor:
        create_notification(
            user=doctor,
            notification_type=Notification.NotificationType.LAB_RESULT_READY,
            title=f"Lab result ready ({analysis['status']}): {lab_request.get_test_name_display()}",
            body=f"{lab_request.patient.full_name} - {lab_request.get_test_name_display()}: {analysis['explanation']}",
            related_object_type="lab_test_result",
            related_object_id=result.id,
        )
        from apps.notifications.tasks import send_doctor_lab_result_email_task
        send_doctor_lab_result_email_task.delay(result.id)

    return {
        "lab_result_id": result.id,
        "ai_status": analysis["status"],
        "ai_risk_level": analysis["risk_level"],
        "doctor_notified": bool(doctor and notify_doctor),
    }
