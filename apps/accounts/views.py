from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy


class AdminLoginView(LoginView):
    """管理员业务登录入口（与 Django Admin 路径独立）。"""

    template_name = "accounts/admin_login.html"
    redirect_authenticated_user = True
    # 登录成功后跳转管理员查询后台，而非 Django Admin
    success_url = reverse_lazy("students:admin_student_list")
