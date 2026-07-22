from django.urls import path
from django.views.generic import TemplateView

from .views import AdminStudentDetailView, AdminStudentListView

app_name = "students"

urlpatterns = [
    path("me/", TemplateView.as_view(template_name="students/student_profile.html"), name="student_profile"),
    path("admin/students/", AdminStudentListView.as_view(), name="admin_student_list"),
    path("admin/students/<int:pk>/", AdminStudentDetailView.as_view(), name="admin_student_detail"),
]
