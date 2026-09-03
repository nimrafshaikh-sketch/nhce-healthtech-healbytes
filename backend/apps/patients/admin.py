from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["full_name", "doctor", "is_linked", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["full_name", "caretaker_name", "doctor__email"]
