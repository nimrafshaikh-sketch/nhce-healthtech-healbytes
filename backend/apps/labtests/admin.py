from django.contrib import admin

from .models import LabTestRequest, LabTestResult


@admin.register(LabTestRequest)
class LabTestRequestAdmin(admin.ModelAdmin):
    list_display = ["test_name", "patient", "requested_by", "assigned_lab_tech", "status", "priority"]
    list_filter = ["status", "priority", "test_name"]
    search_fields = ["patient__full_name"]


@admin.register(LabTestResult)
class LabTestResultAdmin(admin.ModelAdmin):
    list_display = ["request", "recorded_by", "reviewed_by", "reviewed_at"]
