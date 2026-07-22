from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import TemplateView

from .views import AdminLoginView

app_name = "accounts"

urlpatterns = [
    path("student-login/", TemplateView.as_view(template_name="accounts/student_login.html"), name="student_login"),
    path("admin-login/", AdminLoginView.as_view(), name="admin_login"),
    path("admin-logout/", LogoutView.as_view(next_page="/"), name="admin_logout"),
]
