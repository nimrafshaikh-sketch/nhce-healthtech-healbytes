from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class DailyCheckin(TimeStampedModel):
    """A patient's self-reported daily check-in."""

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="checkins")

    checkin_date = models.DateField(auto_now_add=True)
    symptoms = models.TextField(blank=True)
    severity_score = models.IntegerField(null=True, blank=True)
    duration = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    ai_risk_level = models.TextField(blank=True, null=True)
    ai_risk_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ai_reason = models.TextField(blank=True, null=True)
    ai_recommended_action = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-checkin_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["patient", "checkin_date"], name="unique_patient_checkin_per_day")
        ]

    def __str__(self):
        return f"{self.patient.name} check-in {self.checkin_date}"
