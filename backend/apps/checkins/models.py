from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class DailyCheckin(TimeStampedModel):
    """A patient's self-reported daily check-in.

    IMPORTANT: this app does NOT do medical diagnosis/risk analysis itself -
    that is the AI engine's job (separate module/service). This model just
    stores the patient's raw input plus whatever risk verdict the AI engine
    later returns for it (apps.checkins.ai_client / apps.checkins.tasks).
    """

    class RiskLevel(models.TextChoices):
        PENDING = "pending", "Pending AI analysis"
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        UNAVAILABLE = "unavailable", "AI engine unavailable"

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="checkins")

    checkin_date = models.DateField(default=timezone.localdate, help_text="Calendar date this check-in is for (patient-local).")
    symptoms = models.JSONField(default=list, blank=True, help_text="List of symptom strings selected by patient.")
    mood = models.CharField(max_length=50, blank=True)
    pain_level = models.PositiveSmallIntegerField(null=True, blank=True, help_text="0-10 self-reported scale.")
    notes = models.TextField(blank=True)
    vitals = models.JSONField(default=dict, blank=True, help_text='e.g. {"temperature_c": 37.2, "heart_rate": 78}')

    ai_risk_level = models.CharField(max_length=15, choices=RiskLevel.choices, default=RiskLevel.PENDING)
    ai_risk_score = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="AI engine's riskScore, 0.0-1.0.",
    )
    ai_notes = models.TextField(blank=True, help_text="AI engine's 'reason' text.")
    ai_recommended_action = models.TextField(blank=True, help_text="AI engine's 'recommendedAction'.")
    ai_notification_recipient = models.CharField(
        max_length=30, blank=True,
        help_text="AI engine's suggested recipient - informational only, NOT used for routing "
                   "(the backend decides routing via apps.alerts.rules based on ai_risk_level).",
    )
    ai_processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-checkin_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["patient", "checkin_date"], name="unique_patient_checkin_per_day")
        ]

    def __str__(self):
        return f"{self.patient.full_name} check-in {self.checkin_date} ({self.ai_risk_level})"
