from django.contrib.auth import logout as auth_logout
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from apps.accounts.forms import StudentLoginForm
from apps.accounts.student_access import SESSION_STUDENT_ID_KEY
from apps.students.models import Student

LOGIN_ERROR_MESSAGE = "姓名或学号不正确"


# ═══════════════════════════════════════════════════════════
# 管理员登录 / 退出（成员5）
# ═══════════════════════════════════════════════════════════

class AdminLoginView(LoginView):
    """管理员业务登录入口（与 Django Admin 路径独立）。"""

    template_name = "accounts/admin_login.html"
    redirect_authenticated_user = False
    # 登录成功后跳转管理员查询后台，而非 Django Admin
    success_url = reverse_lazy("students:admin_student_list")

    def dispatch(self, request, *args, **kwargs):
        from apps.accounts.permissions import check_admin_role
        from apps.accounts.models import AdminRole

        if check_admin_role(request.user, AdminRole.VIEWER_ADMIN, AdminRole.DATA_ADMIN):
            return redirect(self.get_success_url())
        if request.user.is_authenticated:
            auth_logout(request)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """登录成功后切换为唯一的管理员身份并写入审计日志。"""
        self.request.session.pop(SESSION_STUDENT_ID_KEY, None)
        response = super().form_valid(form)
        user = self.request.user
        # 写入登录审计日志
        from apps.audit.services import record_operation_log
        record_operation_log(
            self.request,
            action="admin_login",
            target_type="admin",
            target_id=str(user.pk),
            description=f"管理员 {user.display_name or user.username} 登录",
        )
        return response


@require_POST
def admin_logout_view(request):
    """管理员退出：仅接受 POST，清除 Session 并写入审计日志。"""
    from apps.audit.services import record_operation_log
    user = request.user
    if user.is_authenticated:
        record_operation_log(
            request,
            action="admin_logout",
            target_type="admin",
            target_id=str(user.pk),
            description=f"管理员 {user.display_name or user.username} 退出",
        )
    auth_logout(request)
    return redirect("/")


# ═══════════════════════════════════════════════════════════
# 学生登录 / 退出（成员3）
# ═══════════════════════════════════════════════════════════

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
                # 学生端与管理员端身份互斥，避免旧管理员会话泄露后台权限。
                auth_logout(request)
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
