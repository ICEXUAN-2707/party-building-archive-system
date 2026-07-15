from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AdminUser


@admin.register(AdminUser)
class AdminUserAdmin(UserAdmin):
    list_display = ("username", "display_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "display_name")
    readonly_fields = ("created_at", "last_login", "date_joined")
    fieldsets = UserAdmin.fieldsets + (
        ("项目角色", {"fields": ("display_name", "role", "created_at")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("项目角色", {"fields": ("display_name", "role")}),
    )
