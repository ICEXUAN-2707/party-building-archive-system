from django.shortcuts import render
from apps.students.models import Student

def student_profile(request):
    # 临时无鉴权，待accounts模块补齐student_session后再接入登录拦截
    student = Student.objects.first()

    context = {
        "student": student,
        # 主干无这两张模型，固定为空列表，模板空判断正常展示
        "application_records": [],
        "idea_reports": [],
        "report_count": 0,
        "latest_report": None,
        "is_count_from_system": True
    }
    return render(request, "students/student_profile.html", context)
