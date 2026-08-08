from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # 学生登录
    path("login/", views.student_login, name="student_login"),
    # 管理员登录
    path("admin-login/", views.admin_login, name="admin_login"),
    # 学生登出
    path("logout/", views.student_logout, name="student_logout"),
]
