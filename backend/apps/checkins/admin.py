from django.contrib import admin

from .models import DailyCheckin


@admin.register(DailyCheckin)
class DailyCheckinAdmin(admin.ModelAdmin):
    list_display = ["patient", "checkin_date", "ai_risk_level", "created_at"]
    list_filter = ["ai_risk_level"]
    search_fields = ["patient__full_name"]
