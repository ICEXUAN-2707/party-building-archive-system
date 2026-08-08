from django.shortcuts import render, redirect
# 兼容成员3未合入student_session模块
try:
    from apps.accounts.student_session import get_current_student, student_required
except ModuleNotFoundError:
    def get_current_student(request):
        sid = request.session.get("student_id")
        if not sid:
            return None
        try:
            from .models import Student
            return Student.objects.get(id=sid, status="active")
        except Student.DoesNotExist:
            request.session.pop("student_id", None)
            return None

    def student_required(view_func):
        def wrapper(request, *args, **kwargs):
            stu = get_current_student(request)
            if stu is None:
                return redirect("accounts:student_login")
            return view_func(request, *args, **kwargs)
        return wrapper

from .models import ApplicationRecord, IdeologicalReport

@student_required
def student_profile(request):
    student = get_current_student(request)
    application = ApplicationRecord.objects.filter(student=student).first()
    report_list = IdeologicalReport.objects.filter(student=student, is_active=True).order_by("sequence_number")

    if application and application.reported_total_count is not None:
        # 模型没有 report_count，改用模型已有的 reported_total_count
        report_count = application.reported_total_count
        is_count_from_system = False
    else:
        report_count = report_list.count()
        is_count_from_system = True

    context = {
        "student": student,
        "application": application,
        "report_list": report_list,
        "report_count": report_count,
        "is_count_from_system": is_count_from_system
    }
    return render(request, "students/student_profile.html", context)
