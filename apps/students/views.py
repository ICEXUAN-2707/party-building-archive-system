from django.shortcuts import render

from apps.accounts.student_access import student_required
from apps.materials.models import (
    ApplicationRecord,
    IdeologicalReport,
    IdeologicalReportSummary,
)

def _compute_last_updated(student, application_record, report_summary, idea_reports):
    """最近更新时间：取当前档案相关系统记录时间的最大值。

    候选字段（仅取非空）：
    - Student.updated_at
    - ApplicationRecord.updated_at
    - IdeologicalReportSummary.updated_at
    - 有效 IdeologicalReport.created_at 的最大值

    submitted_at 仅代表业务提交日期，不参与更新时间计算。
    """
    candidates = [student.updated_at]
    if application_record is not None:
        candidates.append(application_record.updated_at)
    if report_summary is not None:
        candidates.append(report_summary.updated_at)
    if idea_reports:
        latest_report_created = max(report.created_at for report in idea_reports)
        candidates.append(latest_report_created)
    # 过滤掉 None（updated_at 字段理论上都有值，防御性处理）
    valid = [value for value in candidates if value is not None]
    return max(valid) if valid else None

@student_required
def student_profile(request):
    """学生个人档案只读页面。

    身份由成员3的 ``student_required`` 提供，固定为 ``request.current_student``。
    只读取本人关联数据，不写入任何模型，不接受请求参数中的目标学生ID。
    """
    student = request.current_student

    # 入党申请记录：OneToOne 反向访问，缺失时为 None
    try:
        application_record = student.application_record
    except ApplicationRecord.DoesNotExist:
        application_record = None

    # 思想汇报汇总：OneToOne 反向访问，缺失时为 None
    try:
        report_summary = student.report_summary
    except IdeologicalReportSummary.DoesNotExist:
        report_summary = None

    # 思想汇报明细：限定本人且有效，按序号升序
    idea_reports = list(
        IdeologicalReport.objects.filter(student=student, is_active=True).order_by("sequence_number")
    )

    # 最近更新时间：当前档案相关系统记录时间的最大值
    last_updated = _compute_last_updated(
        student, application_record, report_summary, idea_reports
    )

    # 总篇数：优先 Excel 填报值（含0）；为 None 时回退系统计算值并标记来源
    if report_summary is not None and report_summary.reported_total_count is not None:
        report_count = report_summary.reported_total_count
        is_count_from_system = False
    elif report_summary is not None:
        report_count = report_summary.calculated_date_count
        is_count_from_system = True
    else:
        # 无汇总记录时回退有效明细数量，标记为系统计算来源
        report_count = len(idea_reports)
        is_count_from_system = True

    context = {
        "student": student,
        "application_record": application_record,
        "application_records": [application_record] if application_record else [],
        "idea_reports": idea_reports,
        "report_count": report_count,
        "last_updated": last_updated,
        "is_count_from_system": is_count_from_system,
    }
    return render(request, "students/student_profile.html", context)
