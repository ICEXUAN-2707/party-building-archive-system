from django.urls import path
from django.views.generic import TemplateView

from apps.accounts.decorators import admin_url_forbid_student
from apps.students.views import student_profile

app_name = "students"

urlpatterns = [
    path("me/", student_profile, name="student_profile"),
    path(
        "admin/students/",
        admin_url_forbid_student(
            TemplateView.as_view(template_name="students/admin_student_list.html")
        ),
        name="admin_student_list",
    ),
    path(
        "admin/students/<int:pk>/",
        admin_url_forbid_student(
            TemplateView.as_view(template_name="students/admin_student_detail.html")
        ),
        name="admin_student_detail",
    ),
]