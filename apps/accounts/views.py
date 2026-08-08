from django.shortcuts import redirect, render
from django.urls import reverse

def student_login(request):
    """学生登录占位视图，等待成员3正式鉴权接口"""
    return render(request, "accounts/login.html")

def student_logout(request):
    """仅支持POST登出，只清除学生session，不影响管理员登录"""
    if request.method != "POST":
        return redirect("accounts:student_login")
    # 只删除学生会话标识，保留管理员session
    request.session.pop("student_id", None)
    return redirect("home")
