from django.urls import path

from . import views  # 学生登录/退出（成员3）
from .views import AdminLoginView, admin_logout_view  # 管理员登录/退出（成员5）

app_name = "accounts"

urlpatterns = [
    # 学生认证（成员3）
    path("student-login/", views.student_login, name="student_login"),
    path("student-logout/", views.student_logout, name="student_logout"),
    # 管理员认证（成员5）
    path("admin-login/", AdminLoginView.as_view(), name="admin_login"),
    path("admin-logout/", admin_logout_view, name="admin_logout"),
]
