from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Patient(TimeStampedModel):
    """A patient profile, always linked to exactly one Doctor.

    The linked `user` account is created at invitation-code redemption time.
    Until redeemed, `user` is null and the record exists only as the doctor's draft entry.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="patient_profile", null=True, blank=True,
    )
    doctor = models.ForeignKey(
        "accounts.Doctor", on_delete=models.RESTRICT,
        related_name="patients",
    )

    name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    mobile_number = models.CharField(max_length=20, blank=True, null=True)
    
    caretaker_name = models.CharField(max_length=150, blank=True, null=True)
    caretaker_email = models.EmailField(blank=True, null=True)

    invitation_code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    invitation_code_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} (Dr. {self.doctor.user.name or self.doctor.user.username})"

    @property
    def is_linked(self):
        return self.user_id is not None

