from django.db import models

from apps.core.models import TimeStampedModel


class QRScanLog(TimeStampedModel):
    """Audit trail of QR verification attempts, so patients/doctors can see
    who accessed history via QR scan and when. Not the token itself (the
    token is a signed JWT, never persisted - see apps.qr.tokens).
    """
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="qr_scan_logs")
    scanned_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="qr_scans_performed",
    )
    success = models.BooleanField()
    failure_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]
