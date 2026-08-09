from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.forms import StudentLoginForm
from apps.accounts.student_access import SESSION_STUDENT_ID_KEY
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
                # 轮换会话键防止 Session fixation，同时保留管理员认证数据。
                request.session.cycle_key()
                request.session[SESSION_STUDENT_ID_KEY] = student.id
                return redirect("students:student_profile")
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
    request.session.pop(SESSION_STUDENT_ID_KEY, None)
    return redirect("accounts:student_login")
