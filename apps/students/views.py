from django.db.models import Max, Prefetch, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.generic import DetailView, ListView

from apps.accounts.permissions import ViewerOrDataAdminRequiredMixin
from apps.accounts.student_access import student_required
from apps.materials.models import (
    ApplicationRecord,
    IdeologicalReport,
    IdeologicalReportSummary,
)
from .models import DevelopmentStage, PartyBranch, Student, StudentStatus


# ═══════════════════════════════════════════════════════════
# 管理员学生列表 / 详情（成员5）
# ═══════════════════════════════════════════════════════════

class AdminStudentListView(ViewerOrDataAdminRequiredMixin, ListView):
    """管理员学生列表：展示8个字段，支持5类筛选、分页。"""

    model = Student
    template_name = "students/admin_student_list.html"
    context_object_name = "students"
    paginate_by = 20

    # 预取关联支部，避免 N+1 查询
    queryset = Student.objects.select_related("branch").order_by("student_number")

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.GET
        self.filter_errors = []

        # 姓名：模糊匹配
        name = params.get("name", "").strip()
        if name:
            qs = qs.filter(name__icontains=name)

        # 学号：模糊匹配
        student_number = params.get("student_number", "").strip()
        if student_number:
            qs = qs.filter(student_number__icontains=student_number)

        # 支部：精确匹配，校验整数
        branch_id = params.get("branch", "").strip()
        if branch_id:
            if branch_id.isdigit():
                branch_pk = int(branch_id)
                if branch_pk > 0 and PartyBranch.objects.filter(pk=branch_pk).exists():
                    qs = qs.filter(branch_id=branch_pk)
                else:
                    self.filter_errors.append("所选党支部不存在。")
            else:
                self.filter_errors.append("党支部筛选值无效。")

        # 发展阶段：精确匹配，校验合法值
        stage = params.get("stage", "").strip()
        if stage:
            valid_stages = {s.value for s in DevelopmentStage}
            if stage in valid_stages:
                qs = qs.filter(development_stage=stage)
            else:
                self.filter_errors.append("发展阶段筛选值无效。")

        # 学生状态：精确匹配，校验合法值
        status = params.get("status", "").strip()
        if status:
            valid_statuses = {s.value for s in StudentStatus}
            if status in valid_statuses:
                qs = qs.filter(status=status)
            else:
                self.filter_errors.append("学生状态筛选值无效。")

        if self.filter_errors:
            return qs.none()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["branches"] = PartyBranch.objects.filter(is_active=True)
        context["stages"] = DevelopmentStage.choices
        context["statuses"] = StudentStatus.choices
        context["filters"] = self.request.GET.dict()
        context["filter_errors"] = self.filter_errors
        return context


class AdminStudentDetailView(ViewerOrDataAdminRequiredMixin, DetailView):
    """管理员学生详情：展示完整党务材料信息与统计汇总。"""

    model = Student
    template_name = "students/admin_student_detail.html"
    context_object_name = "student"

    def get_queryset(self):
        return (
            Student.objects
            .select_related("branch", "source_import_batch")
            .prefetch_related(
                "application_record",
                "report_summary",
                Prefetch(
                    "ideological_reports",
                    queryset=IdeologicalReport.objects.filter(is_active=True).order_by("sequence_number"),
                ),
            )
        )

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # 写入查看详情审计日志
        from apps.audit.services import record_operation_log

        student = self.object
        record_operation_log(
            request,
            action="view_student_detail",
            target_type="student",
            target_id=str(student.pk),
            description="查看学生档案详情",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object
        try:
            application_record = student.application_record
        except ApplicationRecord.DoesNotExist:
            application_record = None
        try:
            report_summary = student.report_summary
        except IdeologicalReportSummary.DoesNotExist:
            report_summary = None

        idea_reports = list(student.ideological_reports.all())
        update_candidates = [student.updated_at]
        if application_record is not None:
            update_candidates.append(application_record.updated_at)
        if report_summary is not None:
            update_candidates.append(report_summary.updated_at)
        update_candidates.extend(report.created_at for report in idea_reports)
        profile_updated_at = max(value for value in update_candidates if value is not None)

        reported_total_count = (
            report_summary.reported_total_count if report_summary is not None else None
        )
        calculated_date_count = (
            report_summary.calculated_date_count if report_summary is not None else len(idea_reports)
        )
        if reported_total_count is not None:
            report_count = reported_total_count
            report_count_source = "excel"
        else:
            report_count = calculated_date_count
            report_count_source = "system"

        context.update(
            application_record=application_record,
            report_summary=report_summary,
            idea_reports=idea_reports,
            reported_total_count=reported_total_count,
            calculated_date_count=calculated_date_count,
            report_count=report_count,
            report_count_source=report_count_source,
            profile_updated_at=profile_updated_at,
        )
        return context


# ═══════════════════════════════════════════════════════════
# 学生个人页（成员4）
# ═══════════════════════════════════════════════════════════

@student_required
def student_profile(request: HttpRequest) -> HttpResponse:
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
    # 页面最近更新时间反映当前档案记录在系统内的最后变更时间，
    # 不得使用思想汇报的业务提交日期 submitted_at 冒充更新时间。
    report_created_at = IdeologicalReport.objects.filter(
        student=student,
        is_active=True,
    ).aggregate(latest=Max("created_at"))["latest"]
    update_candidates = [student.updated_at, report_created_at]
    if application_record is not None:
        update_candidates.append(application_record.updated_at)
    if report_summary is not None:
        update_candidates.append(report_summary.updated_at)
    profile_updated_at = max(value for value in update_candidates if value is not None)

    # 学生页主数字必须与下方当前有效明细严格一致。Excel 填报值仅作为
    # 原始数据保留；不一致时单独提示，避免出现“总数4、明细3”的误导。
    report_count = len(idea_reports)
    reported_total_count = (
        report_summary.reported_total_count if report_summary is not None else None
    )
    report_count_mismatch = (
        reported_total_count is not None and reported_total_count != report_count
    )

    context = {
        "student": student,
        "application_record": application_record,
        "idea_reports": idea_reports,
        "report_count": report_count,
        "reported_total_count": reported_total_count,
        "report_count_mismatch": report_count_mismatch,
        "profile_updated_at": profile_updated_at,
    }
    return render(request, "students/student_profile.html", context)
