from django.urls import path
from django.views.generic import TemplateView

from apps.accounts.student_access import get_current_student
from apps.students.views import student_profile

app_name = "students"

def _student_forbidden(request):
    """学生已登录时禁止访问管理员页面。"""
    if get_current_student(request) is not None:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("无权访问管理员页面")
    return None

def _admin_guard(view):
    from functools import wraps
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        result = _student_forbidden(request)
        if result is not None:
            return result
        return view(request, *args, **kwargs)
    return _wrapped

urlpatterns = [
    path("me/", student_profile, name="student_profile"),
    path(
        "admin/students/",
        _admin_guard(TemplateView.as_view(template_name="students/admin_student_list.html")),
        name="admin_student_list",
    ),
    path(
        "admin/students/<int:pk>/",
        _admin_guard(TemplateView.as_view(template_name="students/admin_student_detail.html")),
        name="admin_student_detail",
    ),
]
