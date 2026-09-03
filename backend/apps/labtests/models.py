from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class LabTestRequest(TimeStampedModel):
    """A doctor's order for a lab test on a patient.

    test_name is a fixed choice list (not free text) so the AI engine's
    explanation/reference-range lookup has a reliable key to match against -
    approved strawman list, confirm with Member 4 if their table uses
    different keys.
    """

    class TestName(models.TextChoices):
        CBC = "CBC", "Complete Blood Count"
        BLOOD_GLUCOSE = "BLOOD_GLUCOSE", "Blood Glucose"
        LIPID_PROFILE = "LIPID_PROFILE", "Lipid Profile"
        HBA1C = "HBA1C", "HbA1c"
        KFT = "KFT", "Kidney Function Test"
        LFT = "LFT", "Liver Function Test"
        TFT = "TFT", "Thyroid Function Test"
        URINALYSIS = "URINALYSIS", "Urinalysis"

    class Priority(models.TextChoices):
        ROUTINE = "routine", "Routine"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="lab_test_requests")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="lab_tests_requested", limit_choices_to={"role": "doctor"},
    )
    assigned_lab_tech = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lab_tests_assigned", limit_choices_to={"role": "lab_tech"},
        help_text="Null until a lab tech claims it - see LabTestClaimView.",
    )

    test_name = models.CharField(max_length=20, choices=TestName.choices)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.ROUTINE)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.REQUESTED)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_test_name_display()} for {self.patient.full_name} ({self.status})"


class LabTestResult(TimeStampedModel):
    """The result for a LabTestRequest. No file upload - there's no file
    storage configured in this build; result_text only.
    """
    request = models.OneToOneField(LabTestRequest, on_delete=models.CASCADE, related_name="result")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="lab_results_recorded", limit_choices_to={"role": "lab_tech"},
    )
    result_text = models.TextField()
    notes = models.TextField(blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lab_results_reviewed", limit_choices_to={"role": "doctor"},
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Result for {self.request}"
