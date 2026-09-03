from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["name", "doctor", "mobile_number", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "mobile_number", "doctor__user__name", "doctor__user__username"]
