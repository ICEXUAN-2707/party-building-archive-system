import time

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.accounts.decorators import (
    SESSION_STUDENT_ID_KEY,
    admin_url_forbid_student,
    student_login_required,
)
from apps.accounts.forms import StudentLoginForm
from apps.students.models import Student, StudentStatus

LOGIN_ERROR_MESSAGE = "姓名或学号不匹配"
LOCKOUT_ERROR_MESSAGE = "登录失败次数过多，请 5 分钟后再试"

SESSION_FAILED_COUNT_KEY = "_student_login_failed_count"
SESSION_LOCKED_UNTIL_KEY = "_student_login_locked_until"

MAX_LOGIN_FAILURES = 5
LOCK_DURATION_SECONDS = 5 * 60


def _reset_login_throttle(session) -> None:
    session.pop(SESSION_FAILED_COUNT_KEY, None)
    session.pop(SESSION_LOCKED_UNTIL_KEY, None)


def _increment_login_failure(session, now: float) -> None:
    count = int(session.get(SESSION_FAILED_COUNT_KEY, 0) or 0) + 1
    session[SESSION_FAILED_COUNT_KEY] = count
    if count >= MAX_LOGIN_FAILURES:
        session[SESSION_LOCKED_UNTIL_KEY] = now + LOCK_DURATION_SECONDS


def _is_login_locked(session, now: float) -> bool:
    locked_until = session.get(SESSION_LOCKED_UNTIL_KEY)
    if locked_until is None:
        return False
    try:
        locked_until_float = float(locked_until)
    except (TypeError, ValueError):
        return False
    if locked_until_float <= now:
        _reset_login_throttle(session)
        return False
    return True


def student_login(request: HttpRequest) -> HttpResponse:
    now = time.time()
    locked = request.method == "POST" and _is_login_locked(request.session, now)
    if request.method == "POST" and not locked:
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            student_number = form.cleaned_data["student_number"]
            student = (
                Student.objects.filter(
                    name=name,
                    student_number=student_number,
                    status=StudentStatus.ACTIVE,
                )
                .select_related("branch")
                .first()
            )
            if student is not None:
                _reset_login_throttle(request.session)
                request.session[SESSION_STUDENT_ID_KEY] = student.id
                return redirect(reverse("students:student_profile"))
            _increment_login_failure(request.session, now)
            if _is_login_locked(request.session, now):
                form.add_error(None, LOCKOUT_ERROR_MESSAGE)
            else:
                form.add_error(None, LOGIN_ERROR_MESSAGE)
        else:
            for field_name in list(form.errors.keys()):
                if field_name != "__all__":
                    del form.errors[field_name]
            _increment_login_failure(request.session, now)
            if _is_login_locked(request.session, now):
                form.add_error(None, LOCKOUT_ERROR_MESSAGE)
            else:
                form.add_error(None, LOGIN_ERROR_MESSAGE)
    elif locked:
        form = StudentLoginForm(request.POST)
        form.add_error(None, LOCKOUT_ERROR_MESSAGE)
    else:
        form = StudentLoginForm()
    return render(request, "accounts/student_login.html", {"form": form})


def student_logout(request: HttpRequest) -> HttpResponse:
    if SESSION_STUDENT_ID_KEY in request.session:
        del request.session[SESSION_STUDENT_ID_KEY]
    return redirect(reverse("accounts:student_login"))
