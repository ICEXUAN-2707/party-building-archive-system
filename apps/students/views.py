from django.shortcuts import render
# 按契约引入成员3统一认证工具（等待develop合入后生效）
# 修改之后
from ..accounts.student_access import get_current_student, student_required
from .models import Student, ApplicationRecord, IdeologicalReport


@student_required
def student_profile(request):
    # 获取当前登录学生，自动处理无效Session/未登录跳转
    student = get_current_student(request)
    # 查询本人入党申请记录
    application = ApplicationRecord.objects.filter(student=student).first()
    # 查询本人有效思想汇报，按sequence_number升序
    report_list = IdeologicalReport.objects.filter(
        student=student,
        is_active=True
    ).order_by("sequence_number")

    # 处理汇报总数展示规则
    if application and application.reported_total_count is not None:
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
        "is_count_from_system": is_count_from_system,
    }
    return render(request, "students/student_profile.html", context)
