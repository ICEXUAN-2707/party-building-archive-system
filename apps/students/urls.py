from django.urls import path
from . import views

app_name = "students"

urlpatterns = [
    path("profile/", views.student_profile, name="student_profile"),
]
