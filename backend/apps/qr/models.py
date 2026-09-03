from django.db import models
from apps.core.models import TimeStampedModel

class QRAccess(TimeStampedModel):
    class AccessStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        GRANTED = "GRANTED", "Granted"
        DENIED = "DENIED", "Denied"
        EXPIRED = "EXPIRED", "Expired"
        REVOKED = "REVOKED", "Revoked"

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="qr_access_logs")
    token = models.TextField(unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    accessed_by = models.TextField(blank=True, null=True)
    access_status = models.CharField(max_length=15, choices=AccessStatus.choices, default=AccessStatus.PENDING)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"QR for {self.patient.name} ({self.access_status})"
