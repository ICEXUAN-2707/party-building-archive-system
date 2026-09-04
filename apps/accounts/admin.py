from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.audit.services import record_operation_log

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

    def save_model(self, request, obj, form, change):
        old_role = None
        if change and obj.pk:
            old_role = AdminUser.objects.filter(pk=obj.pk).values_list("role", flat=True).first()
        super().save_model(request, obj, form, change)
        if old_role is not None and old_role != obj.role:
            record_operation_log(
                request,
                action="admin_role_changed",
                target_type="AdminUser",
                target_id=str(obj.pk),
                description="管理员角色发生变更",
            )
