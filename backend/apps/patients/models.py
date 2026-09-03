from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Patient(TimeStampedModel):
    """A patient profile, always linked to exactly one Doctor.

    The linked `user` account is created at invitation-code redemption time
    (apps.invitations). Until redeemed, `user` is null and the record exists
    only as the doctor's draft entry (name/caretaker details captured up front,
    per the flow: "Add Patient + Caretaker Details" -> generates invite code).
    """

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="patient_profile", null=True, blank=True,
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="patients", limit_choices_to={"role": "doctor"},
    )

    full_name = models.CharField(max_length=150)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    medical_notes = models.TextField(blank=True, help_text="Non-diagnostic context notes only.")

    # Caretaker details captured by the doctor at patient-creation time
    caretaker_name = models.CharField(max_length=150, blank=True)
    caretaker_relationship = models.CharField(max_length=100, blank=True)
    caretaker_phone_number = models.CharField(max_length=20, blank=True)
    caretaker_email = models.EmailField(blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} (Dr. {self.doctor.get_full_name() or self.doctor.email})"

    @property
    def is_linked(self):
        return self.user_id is not None
