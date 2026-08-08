from django.shortcuts import render, redirect
from django.urls import reverse

def student_login(request):
    """学生登录，渲染student_login.html"""
    return render(request, "accounts/student_login.html")

def admin_login(request):
    """管理员登录，渲染admin_login.html"""
    return render(request, "accounts/admin_login.html")

def student_logout(request):
    """仅POST登出，只清除student_id，不影响管理员session"""
    if request.method != "POST":
        return redirect("accounts:student_login")
    request.session.pop("student_id", None)
    return redirect("home")
