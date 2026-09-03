from django.contrib import admin

from .models import QRAccess


@admin.register(QRAccess)
class QRAccessAdmin(admin.ModelAdmin):
    list_display = ["patient", "expires_at", "used_at", "is_active", "access_status"]
    list_filter = ["is_active", "access_status"]
