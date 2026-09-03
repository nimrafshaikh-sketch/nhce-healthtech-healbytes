from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ["email", "username", "role", "first_name", "last_name", "is_active"]
    list_filter = ["role", "is_active"]
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Role & Profile", {"fields": ("role", "phone_number", "specialization", "license_number")}),
    )
