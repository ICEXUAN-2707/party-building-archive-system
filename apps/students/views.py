from django.shortcuts import render
from .models import ApplicationRecord, IdeologicalReport

# 临时兼容：成员3鉴权模块未合入前规避导入错误，合入后自动生效官方实现
try:
    from apps.accounts.student_session import get_current_student, student_required
except ModuleNotFoundError:
    # 仅作占位，无任何鉴权逻辑，仅保证模块可正常加载
    def student_required(view_func):
        return view_func

    def get_current_student(request):
        return None


@student_required
def student_profile(request):
    # 仅从Session获取当前学生，不接受外部参数传入，杜绝越权切换
    student = get_current_student(request)

    # 查询本人申请记录（一对一关系）
    application = ApplicationRecord.objects.filter(student=student).first()

    # 查询本人有效思想汇报，按真实序号升序排列
    report_list = IdeologicalReport.objects.filter(
        student=student,
        is_active=True
    ).order_by("sequence_number")

    # 冻结规则：汇报总数展示逻辑
    if application is not None and application.reported_total_count is not None:
        # 有填报值（包含0）直接展示填报值
        report_count = application.reported_total_count
        is_count_from_system = False
    else:
        # 无填报值时展示系统实际统计值
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
