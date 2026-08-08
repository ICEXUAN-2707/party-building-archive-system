from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.student_login, name="student_login"),
    path("logout/", views.student_logout, name="student_logout"),
]
