from django.contrib import admin

from .models import EmailNotificationLog, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "notification_type", "title", "is_read", "created_at"]
    list_filter = ["notification_type"]


@admin.register(EmailNotificationLog)
class EmailNotificationLogAdmin(admin.ModelAdmin):
    list_display = ["recipient_type", "recipient_email", "category", "patient", "sent", "created_at"]
    list_filter = ["recipient_type", "category", "sent"]
    search_fields = ["recipient_email", "patient__full_name"]
