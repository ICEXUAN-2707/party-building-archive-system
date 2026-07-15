from django.conf import settings
from django.db import models


class OperationLog(models.Model):
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="操作人",
        related_name="operation_logs",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    operator_role = models.CharField("操作人角色", max_length=32, blank=True)
    action = models.CharField("操作", max_length=64)
    target_type = models.CharField("目标类型", max_length=64, blank=True)
    target_id = models.CharField("目标ID", max_length=64, blank=True)
    description = models.TextField("说明", blank=True)
    ip_address = models.GenericIPAddressField("IP地址", null=True, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "操作日志"
        verbose_name_plural = "操作日志"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.operator_role} {self.action}"
