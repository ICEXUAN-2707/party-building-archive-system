from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Student
from .decorators import student_login_required

def student_login(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        stu_num = request.POST.get("student_num", "").strip()
        student = Student.objects.filter(name=name, student_number=stu_num).first()
        if student:
            request.session["student_id"] = student.id
            return redirect("students:profile")
        else:
            messages.error(request, "姓名或学号不匹配，请检查后重新输入")
    return render(request, "accounts/login.html")

def logout(request):
    request.session.flush()
    return redirect("accounts:student_login")
