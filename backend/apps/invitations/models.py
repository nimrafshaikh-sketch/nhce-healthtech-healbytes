import secrets
import string

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel

CODE_ALPHABET = string.ascii_uppercase + string.digits  # unambiguous-ish, uppercase for easy manual entry
CODE_LENGTH = 8


def generate_invitation_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


class InvitationCode(TimeStampedModel):
    """Single-use code a Doctor generates for a specific (draft) Patient record.
    The Patient enters this code to link their new account to that Doctor.

    Defaults (approved): 8-char alphanumeric, single-use, expires after
    settings.INVITATION_CODE_EXPIRY_MINUTES (15 min default).
    """

    code = models.CharField(max_length=16, unique=True, default=generate_invitation_code, editable=False)
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="invitation_codes", limit_choices_to={"role": "doctor"},
    )
    patient = models.OneToOneField(
        "patients.Patient", on_delete=models.CASCADE, related_name="invitation_code",
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(
                minutes=settings.INVITATION_CODE_EXPIRY_MINUTES
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} -> {self.patient.full_name}"

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.revoked and not self.is_expired
