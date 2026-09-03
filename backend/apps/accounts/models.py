from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    """Custom user for Doctor, Patient, Receptionist, and Lab Technician accounts.

    Doctor: self-registers via apps.accounts.views.DoctorRegisterView.
    Patient: created at invitation-code redemption time, not directly -
    see apps.invitations.
    Receptionist / Lab Technician: internal clinic staff, no public
    registration endpoint - created via Django admin only (approved scope
    for this build; revisit if a self-service or admin-created-by-doctor
    flow is needed later).
    """

    class Role(models.TextChoices):
        DOCTOR = "doctor", "Doctor"
        PATIENT = "patient", "Patient"
        RECEPTIONIST = "receptionist", "Receptionist"
        LAB_TECH = "lab_tech", "Lab Technician"

    role = models.CharField(max_length=15, choices=Role.choices)
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

    @property
    def is_receptionist(self):
        return self.role == self.Role.RECEPTIONIST

    @property
    def is_lab_tech(self):
        return self.role == self.Role.LAB_TECH
