from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Student


def student_login(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        stu_num = request.POST.get("student_num", "").strip()
        student = Student.objects.filter(name=name, student_number=stu_num).first()
        if student:
            request.session["student_id"] = student.id
            return redirect("students:student_profile")
        else:
            messages.error(request, "姓名或学号不匹配，请检查后重新输入")
    return render(request, "accounts/login.html")


def logout(request):
    request.session.flush()
    return redirect("accounts:student_login")


def student_profile(request):
    student_id = request.session.get("student_id")
    if not student_id:
        return redirect("accounts:student_login")
    student = Student.objects.get(id=student_id)
    return render(request, "students/profile.html", {"student": student})


# 新增占位视图，满足测试路由解析
def admin_student_list(request):
    return render(request, "students/admin_student_list.html")


def admin_student_detail(request, pk):
    student = Student.objects.get(pk=pk)
    return render(request, "students/admin_student_detail.html", {"student": student})
