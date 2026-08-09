from django.urls import path
from django.views.generic import TemplateView

app_name = "students"

urlpatterns = [
    path("me/", TemplateView.as_view(template_name="students/student_profile.html"), name="student_profile"),
    path("admin/students/", TemplateView.as_view(template_name="students/admin_student_list.html"), name="admin_student_list"),
    path("admin/students/<int:pk>/", TemplateView.as_view(template_name="students/admin_student_detail.html"), name="admin_student_detail"),
]
