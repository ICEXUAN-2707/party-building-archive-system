from django.contrib.auth.models import AbstractUser
from django.db import models


class AdminRole(models.TextChoices):
    VIEWER_ADMIN = "viewer_admin", "查询管理员"
    DATA_ADMIN = "data_admin", "数据管理员"


class AdminUser(AbstractUser):
    display_name = models.CharField("显示名称", max_length=64, blank=True)
    role = models.CharField(
        "管理员角色",
        max_length=32,
        choices=AdminRole.choices,
        default=AdminRole.VIEWER_ADMIN,
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "管理员用户"
        verbose_name_plural = "管理员用户"
        ordering = ["username"]

    def __str__(self) -> str:
        return self.display_name or self.username
