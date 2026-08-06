from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.accounts.student_access import student_required

@student_required
def student_profile(request: HttpRequest) -> HttpResponse:
    return render(request, "students/student_profile.html", {"student": request.current_student})
