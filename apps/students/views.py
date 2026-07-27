from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.accounts.decorators import admin_url_forbid_student, student_login_required
from apps.students.models import Student


@student_login_required
def student_profile(request: HttpRequest) -> HttpResponse:
    student = Student.objects.filter(pk=request.student_id).select_related("branch").first()  # type: ignore[attr-defined]
    return render(
        request,
        "students/student_profile.html",
        {"student": student, "current_student_id": request.student_id},  # type: ignore[attr-defined]
    )


@admin_url_forbid_student
def admin_student_list(request: HttpRequest) -> HttpResponse:
    return render(request, "students/admin_student_list.html")


@admin_url_forbid_student
def admin_student_detail(request: HttpRequest, pk: int) -> HttpResponse:
    return render(request, "students/admin_student_detail.html", {"pk": pk})
