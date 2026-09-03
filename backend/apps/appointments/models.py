from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Appointment(TimeStampedModel):
    """A scheduled visit between a Patient and a Doctor.

    Can be booked by a Receptionist (front-desk, on behalf of any
    doctor/patient) or by the Doctor themselves (e.g. the "Schedule
    Follow-up" action on a patient's profile). The Patient has no general
    write access - only the two narrow transitions below (confirm/cancel).
    """

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No show"

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="appointments")
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="appointments", limit_choices_to={"role": "doctor"},
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="appointments_booked", help_text="Whoever booked it - Doctor or Receptionist.",
    )

    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SCHEDULED)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"{self.patient.full_name} with Dr. {self.doctor.get_full_name() or self.doctor.email} " \
               f"@ {self.scheduled_at} ({self.status})"
