from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Notification(TimeStampedModel):
    """In-app notification record for a User (Doctor or Patient).
    Scope decision: in-app/DB only, no email/SMS/push in this build.
    """

    class NotificationType(models.TextChoices):
        MEDICATION_REMINDER = "medication_reminder", "Medication reminder"
        ALERT = "alert", "Alert"
        INVITATION = "invitation", "Invitation"
        LAB_TEST_REQUEST = "lab_test_request", "New lab test request"
        GENERAL = "general", "General"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=25, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)

    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)

    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_read(self):
        return self.read_at is not None


class EmailNotificationLog(TimeStampedModel):
    """Audit trail of every outbound notification email (doctor, patient, or
    caretaker). Always written, whether the send succeeds or fails, so any
    email-related question ("did the caretaker actually get notified?") can
    be answered from the API/admin instead of digging through server logs.

    The caretaker has no login/User account in this build (no caretaker
    dashboard was requested) - caretaker_name/caretaker_email are just
    contact fields on Patient (apps.patients.models.Patient), so caretaker
    rows here have recipient_user left null and recipient_email filled in.
    Doctor/patient rows have recipient_user set (their own account).
    """

    class RecipientType(models.TextChoices):
        DOCTOR = "doctor", "Doctor"
        PATIENT = "patient", "Patient"
        CARETAKER = "caretaker", "Caretaker"
        LAB_TECH = "lab_tech", "Lab Technician"

    class Category(models.TextChoices):
        ALERT = "alert", "Doctor alert (high-risk check-in)"
        CHECKIN_RESULT = "checkin_result", "Patient's own check-in risk result"
        CARETAKER_UPDATE = "caretaker_update", "Caretaker check-in update"
        MEDICATION_REMINDER = "medication_reminder", "Medication reminder"
        LAB_TEST_REQUEST = "lab_test_request", "New lab test request (lab technician alert)"

    recipient_type = models.CharField(max_length=10, choices=RecipientType.choices)
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="email_notification_logs",
    )
    recipient_email = models.EmailField()

    category = models.CharField(max_length=25, choices=Category.choices)
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="email_notification_logs",
    )
    checkin = models.ForeignKey(
        "checkins.DailyCheckin", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="email_notification_logs",
    )
    alert = models.ForeignKey(
        "alerts.Alert", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="email_notification_logs",
    )
    medication = models.ForeignKey(
        "medications.Medication", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="email_notification_logs",
    )
    lab_test_request = models.ForeignKey(
        "labtests.LabTestRequest", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="email_notification_logs",
    )

    subject = models.CharField(max_length=200)
    risk_level = models.CharField(max_length=15, blank=True)
    sent = models.BooleanField(default=False)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
