from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.student_login, name="student_login"),
    path("logout/", views.student_logout, name="student_logout"),
    # 新增：管理员登录占位路由，解决 admin_login 反向找不到
    path("admin-login/", views.student_login, name="admin_login"),
]
