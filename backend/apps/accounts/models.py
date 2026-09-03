from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    """Custom user for both Doctor and Patient accounts."""

    class Role(models.TextChoices):
        DOCTOR = "doctor", "Doctor"
        PATIENT = "patient", "Patient"

    role = models.CharField(max_length=10, choices=Role.choices)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)

    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "name"]

    def __str__(self):
        return f"{self.name or self.username} ({self.role})"

    @property
    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    @property
    def is_patient(self):
        return self.role == self.Role.PATIENT


class Doctor(TimeStampedModel):
    """Doctor profile."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_profile")
    specialization = models.CharField(max_length=100, blank=True)
    hospital_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Dr. {self.user.name or self.user.username}"
