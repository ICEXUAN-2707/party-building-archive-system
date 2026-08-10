from django.urls import path
from . import views

urlpatterns = [
    path("me/", views.student_profile, name="student-profile"),
]
