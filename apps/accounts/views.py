from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.forms import StudentLoginForm
from apps.students.models import Student

LOGIN_ERROR_MESSAGE = "姓名或学号不正确"

def student_login(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            student_number = form.cleaned_data["student_number"]
            student = (
                Student.objects.filter(
                    name=name,
                    student_number=student_number,
                )
                .select_related("branch")
                .first()
            )
            if student is not None:
                request.session["student_id"] = student.id
                return redirect(reverse("students:student_profile"))
            form.add_error(None, LOGIN_ERROR_MESSAGE)
        else:
            for field_name in list(form.errors.keys()):
                if field_name != "__all__":
                    del form.errors[field_name]
            form.add_error(None, LOGIN_ERROR_MESSAGE)
    else:
        form = StudentLoginForm()
    return render(request, "accounts/student_login.html", {"form": form})

@require_POST
def student_logout(request: HttpRequest) -> HttpResponse:
    request.session.pop("student_id", None)
    return redirect(reverse("accounts:student_login"))
