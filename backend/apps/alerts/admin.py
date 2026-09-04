from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["patient", "severity", "recipient_role", "status", "created_at"]
    list_filter = ["severity", "recipient_role", "status"]
