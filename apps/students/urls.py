from django.urls import path
from django.http import HttpResponseRedirect
from django.urls import reverse
from . import views

app_name = "students"

# 原有你的业务路由保留
urlpatterns = [
    path("students/", views.student_profile, name="student_profile"),

    # 新增测试需要的管理员命名路由，重定向到原生admin
    path("admin/students/", lambda r: HttpResponseRedirect(reverse("admin:students_student_changelist")), name="admin_student_list"),
    path("admin/students/<int:pk>/", lambda r,pk: HttpResponseRedirect(reverse("admin:students_student_change", args=[pk])), name="admin_student_detail"),
]
