from django.shortcuts import render
from apps.students.models import Student

def student_profile(request):
    student = Student.objects.first()

    if not student:
        ctx = {
            "student": None,
            "application_records": [],
            "idea_reports": [],
            "report_count": 0,
            "latest_report": None,
            "is_count_from_system": True
        }
        return render(request, "students/student_profile.html", ctx)

    # 兜底：如果关联模型还未在主干合并，捕获异常返回空列表
    try:
        application_records = student.applicationrecord_set.all()
    except AttributeError:
        application_records = []

    try:
        idea_reports = student.ideologicalreport_set.filter(is_active=True).order_by("sequence_number")
    except AttributeError:
        idea_reports = []

    report_count = len(idea_reports)
    latest_report = idea_reports.order_by("-submitted_at").first() if idea_reports else None

    # 业务统计规则兼容
    if application_records and len(application_records) > 0 and application_records[0].reported_total_count is not None:
        final_count = application_records[0].reported_total_count
        is_count_from_system = False
    else:
        final_count = report_count
        is_count_from_system = True

    context = {
        "student": student,
        "application_records": application_records,
        "idea_reports": idea_reports,
        "report_count": final_count,
        "latest_report": latest_report,
        "is_count_from_system": is_count_from_system
    }
    return render(request, "students/student_profile.html", context)
