from functools import wraps

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

from .models import AdminRole


def data_admin_required(view_func):
    """要求当前管理员角色为 data_admin，否则返回 403。"""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != AdminRole.DATA_ADMIN:
            raise PermissionDenied("仅数据管理员可访问导入功能。")
        return view_func(request, *args, **kwargs)

    return wrapper
