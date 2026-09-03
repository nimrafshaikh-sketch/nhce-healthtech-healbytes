from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ["patient", "doctor", "scheduled_at", "status", "created_by"]
    list_filter = ["status"]
    search_fields = ["patient__full_name", "doctor__email"]
