from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.accounts.decorators import student_login_required
from apps.accounts.forms import StudentLoginForm
from apps.students.models import Student

@student_login_required
def student_profile(request: HttpRequest) -> HttpResponse:
    try:
        student = Student.objects.select_related("branch").get(pk=request.student_id)
    except Student.DoesNotExist:
        if "student_id" in request.session:
            del request.session["student_id"]
        return render(request, "accounts/student_login.html", {"form": StudentLoginForm()})
    return render(request, "students/student_profile.html", {"student": student})
