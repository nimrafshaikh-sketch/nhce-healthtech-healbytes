from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Medication(TimeStampedModel):
    """A medication prescribed by a Doctor to a Patient."""

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="medications")
    prescribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="prescribed_medications",
    )

    medicine_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, help_text='e.g. "500mg"')
    frequency_per_day = models.IntegerField(help_text="Number of times per day")
    instructions = models.TextField(blank=True, help_text='e.g. "after food"')

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Blank = ongoing")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.medicine_name} ({self.dosage}) - {self.patient.name}"


class MedicationReminder(TimeStampedModel):
    """Specific reminder time slots for a medication."""
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name="reminders")
    reminder_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["reminder_time"]

    def __str__(self):
        return f"Reminder for {self.medication.medicine_name} at {self.reminder_time}"


class MedicationAdherence(TimeStampedModel):
    """Tracking whether a patient took their medication at a specific time."""
    
    class Status(models.TextChoices):
        TAKEN = "TAKEN", "Taken"
        MISSED = "MISSED", "Missed"
        SKIPPED = "SKIPPED", "Skipped"

    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name="adherence_logs")
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="adherence_logs")
    scheduled_time = models.DateTimeField()
    taken_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices)

    class Meta:
        ordering = ["-scheduled_time"]
        constraints = [
            models.UniqueConstraint(fields=["medication", "scheduled_time"], name="unique_medication_adherence_slot")
        ]

    def __str__(self):
        return f"{self.patient.name} - {self.medication.medicine_name} at {self.scheduled_time} ({self.status})"
