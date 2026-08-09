from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "accounts"

urlpatterns = [
    path("student-login/", views.student_login, name="student_login"),
    path("student-logout/", views.student_logout, name="student_logout"),
    path("admin-login/", TemplateView.as_view(template_name="accounts/admin_login.html"), name="admin_login"),
]
