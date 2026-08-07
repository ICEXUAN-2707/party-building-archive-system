from django.shortcuts import render
# 按契约引入成员3统一认证工具（等待develop合入后生效）
from apps.accounts.student_access import get_current_student, student_required
from .models import Student, ApplicationRecord, IdeologicalReport


@student_required
def student_profile(request):
    # 获取当前登录学生，自动处理无效Session/未登录跳转
    student = get_current_student(request)

    # 查询本人入党申请记录
    app_record = ApplicationRecord.objects.filter(student=student).first()
    # 查询本人有效思想汇报，按sequence_number升序
    report_list = IdeologicalReport.objects.filter(
        student=student,
        is_active=True
    ).order_by("sequence_number")

    # 处理汇报总数展示规则
    if app_record and app.reported_total_count is not None:
        total_report = app_record.reported_total_count
        count_source = "Excel填报"
    else:
        total_report = report.count()
        count_source = "系统统计"

    context = {
        "student": student,
        "app_record": app_record,
        "report_list": report_list,
        "total_report": total_report,
        "count_source": count_source
    }
    return render(request, "students/student_profile.html")


# 新增占位视图，满足测试路由解析
def admin_student_list(request):
    return render(request, "students/admin_student_list.html")


def admin_student_detail(request, pk):
    student = Student.objects.get(pk=pk)
    return render(request, "students/admin_student_detail.html", {"student": student})
