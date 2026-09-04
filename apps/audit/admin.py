from django.contrib import admin

from .models import OperationLog
from .services import record_operation_log


class AuditedModelAdmin(admin.ModelAdmin):
    """为通过 Django Admin 执行的关键数据变更写入无 PII 审计记录。"""

    audit_target_type: str | None = None

    def _audit(self, request, action: str, obj) -> None:
        record_operation_log(
            request,
            action=action,
            target_type=self.audit_target_type or obj._meta.label,
            target_id=str(obj.pk),
            description="通过管理后台执行数据变更",
        )

    def log_addition(self, request, obj, message):
        self._audit(request, "record_created", obj)

    def log_change(self, request, obj, message):
        self._audit(request, "record_updated", obj)

    def log_deletion(self, request, obj, object_repr):
        self._audit(request, "record_deleted", obj)


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = ("operator", "operator_role", "action", "target_type", "target_id", "created_at")
    list_filter = ("operator_role", "action", "target_type")
    search_fields = ("action", "target_type", "target_id")
    readonly_fields = (
        "operator",
        "operator_role",
        "action",
        "target_type",
        "target_id",
        "description",
        "ip_address",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
