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
