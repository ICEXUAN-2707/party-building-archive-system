from django.urls import path

from . import views  # 学生个人页（成员4）
from .views import AdminStudentDetailView, AdminStudentListView  # 管理员列表/详情（成员5）

app_name = "students"

urlpatterns = [
    # 学生个人页（成员4）
    path("me/", views.student_profile, name="student_profile"),
    # 管理员学生查询（成员5）
    path("admin/students/", AdminStudentListView.as_view(), name="admin_student_list"),
    path("admin/students/<int:pk>/", AdminStudentDetailView.as_view(), name="admin_student_detail"),
]
