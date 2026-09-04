from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class QRAccessGrant(TimeStampedModel):
    """A bounded-duration authorization grant created when a doctor who is
    NOT the patient's assigned doctor verifies a valid, signed, non-expired
    patient QR token ("multi-doctor consult" access).

    This is the sole authorization boundary for that consulting doctor's
    subsequent document/RAG access to this patient. It is intentionally
    time-bound and only ever created from a real, successful QR
    verification (see apps.qr.views.QRVerifyView) - it is never permanent,
    and creating one never changes `patient.doctor_id` (the patient's
    primary-doctor assignment is untouched by QR access).
    """

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="qr_access_grants",
    )
    doctor = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="qr_access_grants",
    )
    expires_at = models.DateTimeField()
    purpose = models.CharField(max_length=50, default="qr_scan_consultation")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient", "doctor", "expires_at"]),
        ]

    def is_active(self) -> bool:
        return self.expires_at >= timezone.now()

    @classmethod
    def grant(cls, *, patient, doctor, minutes=None, purpose="qr_scan_consultation"):
        """Create a fresh time-bound grant. `minutes` defaults to
        settings.QR_ACCESS_GRANT_MINUTES (10 minutes - one consultation
        window). Each QR verification creates a new grant row (simple,
        fully auditable) rather than mutating an existing one."""
        from django.conf import settings

        minutes = settings.QR_ACCESS_GRANT_MINUTES if minutes is None else minutes
        return cls.objects.create(
            patient=patient,
            doctor=doctor,
            expires_at=timezone.now() + timezone.timedelta(minutes=minutes),
            purpose=purpose,
        )

    @classmethod
    def has_active_grant(cls, *, patient, doctor) -> bool:
        return cls.objects.filter(
            patient=patient, doctor=doctor, expires_at__gte=timezone.now(),
        ).exists()


class QRScanLog(TimeStampedModel):
    """Audit trail of QR verification attempts, so patients/doctors can see
    who accessed history via QR scan and when. Not the token itself (the
    token is a signed JWT, never persisted - see apps.qr.tokens).
    """
    # Nullable: a scan of a malformed/tampered/wrong-type token has no
    # knowable patient at all, but must still be logged (every scan
    # attempt is recorded, success or failure - see apps.qr.views.QRVerifyView).
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="qr_scan_logs", null=True, blank=True,
    )
    scanned_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="qr_scans_performed",
    )
    success = models.BooleanField()
    failure_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]
