from django.urls import path
from django.http import HttpResponseRedirect
from django.urls import reverse
from . import views

app_name = "students"

urlpatterns = [
    path("profile/", views.student_profile, name="student_profile"),
    path("admin/students/", lambda r: HttpResponseRedirect(reverse("admin:students_student_list")), name="admin_student_list"),
    path("admin/students/<int:pk>/", lambda r,pk: HttpResponseRedirect(reverse("admin:students_student_change", args=[pk])), name="admin_student_detail"),
]
