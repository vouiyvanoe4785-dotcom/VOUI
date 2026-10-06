from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Ayden Transit", {"fields": ("role", "partner", "phone", "service", "recap_alertes_email")}),
    )
    list_display = ("username", "get_full_name", "role", "service", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
