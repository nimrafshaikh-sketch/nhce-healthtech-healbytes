from django.contrib import admin

from .models import QRScanLog


@admin.register(QRScanLog)
class QRScanLogAdmin(admin.ModelAdmin):
    list_display = ["patient", "scanned_by", "success", "created_at"]
    list_filter = ["success"]
