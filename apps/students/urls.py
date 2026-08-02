from django.urls import path
from . import views

# 修复：students模块命名空间必须为 students
app_name = "students"

urlpatterns = [
    path("me/", views.student_profile, name="student_profile"),
    path("admin/students/", views.admin_student_list, name="admin_student_list"),
    path("admin/students/<int:pk>/", views.admin_student_detail, name="admin_student_detail"),
]
