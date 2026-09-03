from django.contrib import admin

from .models import InvitationCode


@admin.register(InvitationCode)
class InvitationCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "doctor", "patient", "expires_at", "used_at", "revoked"]
    list_filter = ["revoked"]
    search_fields = ["code", "patient__full_name", "doctor__email"]
