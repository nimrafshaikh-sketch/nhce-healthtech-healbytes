from django.contrib import admin

from .models import Medication, MedicationReminder, MedicationAdherence


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ["medicine_name", "patient", "dosage", "frequency_per_day", "start_date", "end_date"]
    search_fields = ["medicine_name", "patient__name"]


@admin.register(MedicationReminder)
class MedicationReminderAdmin(admin.ModelAdmin):
    list_display = ["medication", "reminder_time", "is_active"]


@admin.register(MedicationAdherence)
class MedicationAdherenceAdmin(admin.ModelAdmin):
    list_display = ["medication", "patient", "scheduled_time", "taken_at", "status"]
