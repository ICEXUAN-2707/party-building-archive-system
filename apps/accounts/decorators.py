from functools import wraps

from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

SESSION_STUDENT_ID_KEY = "student_id"


def student_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        student_id = request.session.get(SESSION_STUDENT_ID_KEY)
        if student_id is None:
            return redirect(reverse("accounts:student_login"))
        request.student_id = student_id  # type: ignore[attr-defined]
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def admin_url_forbid_student(view_func):
    @wraps(view_func)
    def _wrapped_view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.session.get(SESSION_STUDENT_ID_KEY) is not None:
            return HttpResponseForbidden("无权访问管理员页面")
        return view_func(request, *args, **kwargs)

    return _wrapped_view
