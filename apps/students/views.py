from django.shortcuts import render
# 按契约引入成员3统一认证工具（等待develop合入后生效）
# from apps.accounts.student_access import get_current_student, student_required
# 本地models无Student、IdeologicalReport、ApplicationRecord，临时注释模型导入
# from .models import Student, IdeologicalReport

# @student_required
def student_profile(request):
    # 全部变量临时空占位，避免未定义报错
    student = None
    application = None
    report_list = []
    report_count = 0
    is_count_from_system = True

    context = {
        "student": student,
        "application": application,
        "report_list": report_list,
        "report_count": report_count,
        "is_count_from_system": is_count_from_system,
    }
    return render(request, "students/student_profile.html", context)
