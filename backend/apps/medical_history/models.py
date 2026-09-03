from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class MedicalHistory(TimeStampedModel):
    """Historical medical records for a patient."""

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="medical_history")
    
    diagnosis = models.TextField(blank=True, null=True)
    treatment = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    symptoms = models.JSONField(default=list, blank=True, null=True)
    allergies = models.JSONField(default=list, blank=True, null=True)
    previous_relevant_records = models.JSONField(default=list, blank=True, null=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"History for {self.patient.name} on {self.recorded_at.date() if self.recorded_at else ''}"
