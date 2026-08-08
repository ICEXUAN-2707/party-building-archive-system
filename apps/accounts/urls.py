from django.urls import path
from django.views.generic import TemplateView

app_name = "accounts"

urlpatterns = [
    path("student-login/", TemplateView.as_view(template_name="accounts/student_login.html"), name="student_login"),
    path("admin-login/", TemplateView.as_view(template_name="accounts/admin_login.html"), name="admin_login"),
]
