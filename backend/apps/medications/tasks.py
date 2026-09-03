from celery import shared_task
from django.utils import timezone
from django.db.models import Q

from .models import Medication, MedicationReminder, MedicationAdherence


@shared_task
def dispatch_due_medication_reminders():
    now = timezone.localtime()
    today = now.date()
    current_time = now.time()
    
    # Simple match down to the minute
    # Get active reminders where medication is active
    reminders = MedicationReminder.objects.filter(
        is_active=True,
        reminder_time__hour=current_time.hour,
        reminder_time__minute=current_time.minute,
        medication__start_date__lte=today,
    ).filter(
        Q(medication__end_date__isnull=True) | Q(medication__end_date__gte=today)
    ).select_related('medication', 'medication__patient')

    created = 0
    for reminder in reminders:
        medication = reminder.medication
        scheduled_time = now.replace(second=0, microsecond=0)
        log, was_created = MedicationAdherence.objects.get_or_create(
            medication=medication, patient=medication.patient, scheduled_time=scheduled_time,
            defaults={'status': MedicationAdherence.Status.MISSED} # Assuming initial is MISSED until taken
        )
        if was_created:
            created += 1
            _notify_patient_of_reminder.delay(medication.id, log.id)

    return {"reminders_created": created}


@shared_task
def _notify_patient_of_reminder(medication_id, reminder_log_id):
    from apps.notifications.services import create_notification

    medication = Medication.objects.select_related("patient__user").get(id=medication_id)
    if not medication.patient.user_id:
        return
    create_notification(
        user=medication.patient.user,
        notification_type="medication_reminder",
        title=f"Time to take {medication.medicine_name}",
        body=f"{medication.dosage} - {medication.instructions or 'as prescribed'}",
        related_object_type="medication",
        related_object_id=medication.id,
    )

    from apps.notifications.tasks import send_patient_medication_reminder_email_task
    send_patient_medication_reminder_email_task.delay(medication.id)
