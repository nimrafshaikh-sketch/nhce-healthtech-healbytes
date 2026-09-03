from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Alert(TimeStampedModel):
    """A routed alert about a patient."""

    class RecipientType(models.TextChoices):
        DOCTOR = "DOCTOR", "Doctor"
        CARETAKER = "CARETAKER", "Caretaker"
        BOTH = "BOTH", "Both"

    class Status(models.TextChoices):
        UNREAD = "UNREAD", "Unread"
        READ = "READ", "Read"
        RESOLVED = "RESOLVED", "Resolved"

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="alerts")
    checkin = models.ForeignKey(
        "checkins.DailyCheckin", on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts",
    )

    risk_level = models.TextField()
    recipient_type = models.CharField(max_length=25, choices=RecipientType.choices)
    
    title = models.TextField()
    message = models.TextField()
    
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.UNREAD)
    
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    reason = models.TextField(blank=True, null=True)
    follow_up_action = models.TextField(blank=True, null=True)
    
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.risk_level}] {self.patient.name} -> {self.recipient_type}"
