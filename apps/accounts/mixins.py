"""管理员权限 Mixin（兼容重导出）。

所有权限逻辑已集中至 apps.accounts.permissions。
本模块仅做兼容重导出，新代码请直接从 permissions 导入。
"""

from .permissions import DataAdminRequiredMixin  # noqa: F401
