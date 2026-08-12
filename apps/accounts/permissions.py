"""管理员权限工具 — 统一权限接口。

提供给成员7复用：
- check_admin_role(user, *roles) — 运行时角色判断
- ViewerOrDataAdminRequiredMixin — 类视图 Mixin（查询/数据管理员）
- DataAdminRequiredMixin — 类视图 Mixin（仅数据管理员）
- admin_required — 函数视图装饰器
- admin_role_required(*roles) — 函数视图角色装饰器
- data_admin_required — 函数视图装饰器（仅 data_admin）
- viewer_or_data_admin_required — 函数视图装饰器（viewer / data_admin）

禁止在导入模块或其他模块中复制角色判断逻辑。
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .models import AdminRole


# ═══════════════════════════════════════════════════════════
# 核心工具函数
# ═══════════════════════════════════════════════════════════

def check_admin_role(user, *roles: str) -> bool:
    """检查用户是否具备指定角色之一。

    成员7可调用此函数进行运行时权限判断，无需复制角色常量。
    """
    return getattr(user, "role", "") in roles


# ═══════════════════════════════════════════════════════════
# 类视图 Mixin
# ═══════════════════════════════════════════════════════════

class ViewerOrDataAdminRequiredMixin(LoginRequiredMixin):
    """要求当前管理员为 viewer_admin 或 data_admin，否则返回 403。"""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not check_admin_role(request.user, AdminRole.VIEWER_ADMIN, AdminRole.DATA_ADMIN):
            raise PermissionDenied("需要管理员权限。")
        return super().dispatch(request, *args, **kwargs)


class DataAdminRequiredMixin(LoginRequiredMixin):
    """要求当前管理员角色为 data_admin，否则返回 403。"""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not check_admin_role(request.user, AdminRole.DATA_ADMIN):
            raise PermissionDenied("仅数据管理员可访问导入功能。")
        return super().dispatch(request, *args, **kwargs)


# ═══════════════════════════════════════════════════════════
# 函数视图装饰器
# ═══════════════════════════════════════════════════════════

def admin_required(view_func):
    """要求当前用户已作为管理员登录，否则跳转登录页。"""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)

    return wrapper


def admin_role_required(*roles: str):
    """要求当前管理员具备指定角色之一，否则返回 403。

    用法：
        @admin_role_required(AdminRole.VIEWER_ADMIN, AdminRole.DATA_ADMIN)
        def my_view(request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not check_admin_role(request.user, *roles):
                raise PermissionDenied("当前管理员角色无权执行此操作。")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def data_admin_required(view_func):
    """要求当前管理员角色为 data_admin，否则返回 403。"""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not check_admin_role(request.user, AdminRole.DATA_ADMIN):
            raise PermissionDenied("仅数据管理员可访问导入功能。")
        return view_func(request, *args, **kwargs)

    return wrapper


def viewer_or_data_admin_required(view_func):
    """要求当前管理员为 viewer_admin 或 data_admin，否则返回 403。"""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not check_admin_role(request.user, AdminRole.VIEWER_ADMIN, AdminRole.DATA_ADMIN):
            raise PermissionDenied("需要管理员权限。")
        return view_func(request, *args, **kwargs)

    return wrapper
