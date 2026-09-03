from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    """Custom user for both Doctor and Patient accounts.

    Role is fixed at creation time via the registration endpoints
    (apps.accounts.views.DoctorRegisterView / PatientRegisterView).
    A patient's User is created at invitation-code redemption time,
    not directly — see apps.invitations.
    """

    class Role(models.TextChoices):
        DOCTOR = "doctor", "Doctor"
        PATIENT = "patient", "Patient"

    role = models.CharField(max_length=10, choices=Role.choices)
    phone_number = models.CharField(max_length=20, blank=True)

    # Doctor-only professional fields (blank for patients)
    specialization = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=100, blank=True)

    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    @property
    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    @property
    def is_patient(self):
        return self.role == self.Role.PATIENT
