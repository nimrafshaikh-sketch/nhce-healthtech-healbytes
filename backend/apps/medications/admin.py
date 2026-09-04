from django.contrib import admin

from .models import Medication, MedicationReminderLog


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ["name", "patient", "dosage", "frequency", "start_date", "end_date", "is_active"]
    list_filter = ["frequency", "is_active"]
    search_fields = ["name", "patient__full_name"]


@admin.register(MedicationReminderLog)
class MedicationReminderLogAdmin(admin.ModelAdmin):
    list_display = ["medication", "scheduled_for", "sent_at", "acknowledged_at"]
