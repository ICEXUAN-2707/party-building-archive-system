from functools import wraps

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

from apps.students.models import Student

SESSION_STUDENT_ID_KEY = "student_id"


def get_current_student(request: HttpRequest) -> Student | None:
    """从 Session 获取当前登录的学生，无效时清理并返回 None。"""
    student_id = request.session.get(SESSION_STUDENT_ID_KEY)
    if student_id is None:
        return None
    # bool 是 int 的子类，必须显式排除；数字字符串也不符合冻结契约。
    if type(student_id) is not int or student_id <= 0:
        request.session.pop(SESSION_STUDENT_ID_KEY, None)
        return None
    try:
        return Student.objects.select_related("branch").get(pk=student_id)
    except Student.DoesNotExist:
        request.session.pop(SESSION_STUDENT_ID_KEY, None)
        return None


def student_required(view_func):
    """装饰器：未登录或无效 Session 重定向到登录页。"""
    @wraps(view_func)
    def _wrapped_view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        student = get_current_student(request)
        if student is None:
            return redirect(reverse("accounts:student_login"))
        request.current_student = student
        return view_func(request, *args, **kwargs)

    return _wrapped_view
