from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    label = "audit"
    verbose_name = "审计日志"

    def ready(self) -> None:
        from . import sqlite_pragmas  # noqa: F401
