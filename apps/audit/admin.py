from django.contrib import admin

from .models import OperationLog


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = ("operator", "operator_role", "action", "target_type", "target_id", "created_at")
    list_filter = ("operator_role", "action", "target_type")
    search_fields = ("description", "target_id", "operator__username")
    readonly_fields = ("created_at",)
