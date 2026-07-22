from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .models import AdminRole


class DataAdminRequiredMixin(LoginRequiredMixin):
    """要求当前管理员角色为 data_admin，否则返回 403。"""

    def dispatch(self, request, *args, **kwargs):
        # 先由 LoginRequiredMixin 处理未登录用户，重定向到登录页
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != AdminRole.DATA_ADMIN:
            raise PermissionDenied("仅数据管理员可访问导入功能。")
        return super().dispatch(request, *args, **kwargs)
