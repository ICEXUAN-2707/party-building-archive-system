from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import DetailView, ListView

from .models import DevelopmentStage, PartyBranch, Student


class AdminStudentListView(LoginRequiredMixin, ListView):
    """管理员学生列表：展示姓名/学号/支部/阶段，支持多条件筛选。"""

    model = Student
    template_name = "students/admin_student_list.html"
    context_object_name = "students"
    paginate_by = 50  # 1500 条数据下每页 50 条

    # 预取关联支部，避免 N+1 查询
    queryset = Student.objects.select_related("branch").order_by("student_number")

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.GET

        name = params.get("name", "").strip()
        student_number = params.get("student_number", "").strip()
        branch_id = params.get("branch", "").strip()
        stage = params.get("stage", "").strip()

        if name:
            qs = qs.filter(name__icontains=name)
        if student_number:
            qs = qs.filter(student_number__icontains=student_number)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if stage:
            qs = qs.filter(development_stage=stage)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 筛选选项供模板渲染
        context["branches"] = PartyBranch.objects.filter(is_active=True)
        context["stages"] = DevelopmentStage.choices
        # 保留当前筛选参数以便模板回填
        context["filters"] = self.request.GET.dict()
        return context


class AdminStudentDetailView(LoginRequiredMixin, DetailView):
    """管理员学生详情：展示完整党务材料信息。"""

    model = Student
    template_name = "students/admin_student_detail.html"
    context_object_name = "student"

    def get_queryset(self):
        return Student.objects.select_related("branch").prefetch_related(
            "application_record",
            "report_summary",
            "ideological_reports",
        )
