from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Alert(TimeStampedModel):
    """A routed alert about a patient, created from a risky check-in
    (or in future, other triggers). See apps.alerts.rules for the
    routing logic that decides recipient_role/who gets notified.
    """

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class RecipientRole(models.TextChoices):
        DOCTOR = "doctor", "Doctor"
        CARETAKER = "caretaker", "Caretaker"
        DOCTOR_AND_CARETAKER = "doctor_and_caretaker", "Doctor and Caretaker"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="alerts")
    checkin = models.ForeignKey(
        "checkins.DailyCheckin", on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts",
    )

    severity = models.CharField(max_length=10, choices=Severity.choices)
    recipient_role = models.CharField(max_length=25, choices=RecipientRole.choices)
    reason = models.TextField()

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="acknowledged_alerts",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    # Doctor email tracking (see apps.alerts.rules.should_email_doctor - only
    # HIGH severity emails the doctor; medium/low stay dashboard/API-only).
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.severity}] {self.patient.full_name} -> {self.recipient_role}"
