"""管理员权限装饰器（兼容重导出）。

所有权限逻辑已集中至 apps.accounts.permissions。
本模块仅做兼容重导出，新代码请直接从 permissions 导入。
"""

from .permissions import data_admin_required  # noqa: F401
