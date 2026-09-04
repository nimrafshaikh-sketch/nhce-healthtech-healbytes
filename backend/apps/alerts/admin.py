from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["patient", "risk_level", "recipient_type", "status", "created_at"]
    list_filter = ["risk_level", "recipient_type", "status"]
    search_fields = ["patient__name"]
