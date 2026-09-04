"""Celery tasks for medication reminders.

`dispatch_due_medication_reminders` is intended to run every minute via
Celery Beat (see README for the beat schedule entry). It finds medications
whose reminder_times include the current HH:MM, are active today, and
haven't already had a MedicationReminderLog created for this exact minute
slot (enforced by the unique constraint on (medication, scheduled_for)).

Creating a reminder log creates both an in-app Notification and an email
to the patient (apps.notifications) - see notification-system spec.
"""
from celery import shared_task
from django.utils import timezone

from .models import Medication, MedicationReminderLog


@shared_task
def dispatch_due_medication_reminders():
    now = timezone.localtime()
    hhmm = now.strftime("%H:%M")
    today = now.date()
    created = 0

    candidates = Medication.objects.filter(
        reminders_enabled=True,
        is_active=True,
        start_date__lte=today,
    ).filter(
        models_Q_end_date_ok(today)
    )

    for medication in candidates:
        if hhmm not in (medication.reminder_times or []):
            continue
        scheduled_for = now.replace(second=0, microsecond=0)
        log, was_created = MedicationReminderLog.objects.get_or_create(
            medication=medication, scheduled_for=scheduled_for,
        )
        if was_created:
            created += 1
            _notify_patient_of_reminder.delay(medication.id, log.id)

    return {"reminders_created": created}


def models_Q_end_date_ok(today):
    from django.db.models import Q
    return Q(end_date__isnull=True) | Q(end_date__gte=today)


@shared_task
def _notify_patient_of_reminder(medication_id, reminder_log_id):
    from apps.notifications.services import create_notification

    medication = Medication.objects.select_related("patient__user").get(id=medication_id)
    if not medication.patient.user_id:
        return
    create_notification(
        user=medication.patient.user,
        notification_type="medication_reminder",
        title=f"Time to take {medication.name}",
        body=f"{medication.dosage} - {medication.instructions or 'as prescribed'}",
        related_object_type="medication",
        related_object_id=medication.id,
    )

    from apps.notifications.tasks import send_patient_medication_reminder_email_task
    send_patient_medication_reminder_email_task.delay(medication.id)
