from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Medication(TimeStampedModel):
    """A medication prescribed by a Doctor to a Patient, with dosage/frequency
    and a date range. Reminders are derived from `frequency_per_day` +
    `reminder_times` by Celery Beat (see apps.medications.tasks).
    """

    class Frequency(models.TextChoices):
        ONCE_DAILY = "once_daily", "Once daily"
        TWICE_DAILY = "twice_daily", "Twice daily"
        THREE_TIMES_DAILY = "three_times_daily", "Three times daily"
        WEEKLY = "weekly", "Weekly"
        AS_NEEDED = "as_needed", "As needed"

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="medications")
    prescribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="prescribed_medications", limit_choices_to={"role": "doctor"},
    )

    name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, help_text='e.g. "500mg"')
    frequency = models.CharField(max_length=20, choices=Frequency.choices)
    instructions = models.TextField(blank=True, help_text='e.g. "after food"')

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Blank = ongoing")

    reminder_times = models.JSONField(
        default=list,
        help_text='List of "HH:MM" 24h local times to send a reminder each active day, e.g. ["08:00", "20:00"]',
    )
    reminders_enabled = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.dosage}) - {self.patient.full_name}"

    def is_active_on(self, date):
        if not self.is_active:
            return False
        if date < self.start_date:
            return False
        if self.end_date and date > self.end_date:
            return False
        return True


class MedicationReminderLog(TimeStampedModel):
    """One row per reminder actually dispatched, so Celery Beat's periodic
    task doesn't send duplicates and the patient/doctor can see reminder history.
    """
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name="reminder_logs")
    scheduled_for = models.DateTimeField()
    sent_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-scheduled_for"]
        constraints = [
            models.UniqueConstraint(fields=["medication", "scheduled_for"], name="unique_medication_reminder_slot")
        ]


class Prescription(TimeStampedModel):
    """A doctor-issued prescription for a patient."""

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="prescriptions")
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="prescriptions_issued", limit_choices_to={"role": "doctor"},
    )
    
    medication_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    instructions = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.medication_name} prescribed to {self.patient.full_name} by Dr. {getattr(self.doctor, 'last_name', self.doctor)}"

