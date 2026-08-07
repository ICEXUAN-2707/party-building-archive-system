from django.urls import path
from django.http import HttpResponseRedirect
from django.urls import reverse
from . import views

app_name = "students"

urlpatterns = [
    # 个人主页
    path("profile/", views.student_profile, name="student_profile"),
    # 测试需要的管理员路由
    path("admin/students/", lambda r: HttpResponseRedirect(reverse("admin:students_student_changelist")), name="admin_student_list"),
    path("admin/students/<int:pk>/", lambda r,pk: HttpResponseRedirect(reverse("admin:students_student_change", args=[pk])), name="admin_student_detail"),
]
