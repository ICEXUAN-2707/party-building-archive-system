"""管理员查询模块自动化测试。

覆盖：登录/退出、权限矩阵（统一接口）、五类筛选、非法参数、分页、
      详情字段、统计来源、is_active 过滤、审计日志、审计IP、404。
"""

from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import AdminRole, AdminUser
from apps.accounts.permissions import check_admin_role
from apps.audit.models import OperationLog
from apps.audit.services import get_client_ip
from apps.materials.models import IdeologicalReport, IdeologicalReportSummary
from apps.students.models import DevelopmentStage, PartyBranch, Student, StudentStatus


class AdminQueryTestCase(TestCase):
    """管理员查询测试基类：预创建支部、学生、管理员用户。"""

    @classmethod
    def setUpTestData(cls) -> None:
        # 支部
        cls.branch_a = PartyBranch.objects.create(code="A01", name="第一党支部")
        cls.branch_b = PartyBranch.objects.create(code="A02", name="第二党支部")

        # 学生（覆盖不同阶段和状态）
        cls.student1 = Student.objects.create(
            name="张三",
            student_number="20260001",
            branch=cls.branch_a,
            development_stage=DevelopmentStage.ACTIVIST,
            position="班长",
            status=StudentStatus.ACTIVE,
        )
        cls.student2 = Student.objects.create(
            name="李四",
            student_number="20260002",
            branch=cls.branch_b,
            development_stage=DevelopmentStage.PROBATIONARY,
            position="团支书",
            status=StudentStatus.ACTIVE,
        )
        cls.student3 = Student.objects.create(
            name="王五",
            student_number="20260003",
            branch=cls.branch_a,
            development_stage=DevelopmentStage.FULL_MEMBER,
            position="",
            status=StudentStatus.INACTIVE,
        )
        # student4: 仅有计算值（reported_total_count=None），用于统计来源测试
        cls.student4 = Student.objects.create(
            name="赵六",
            student_number="20260004",
            branch=cls.branch_a,
            development_stage=DevelopmentStage.PROBATIONARY,
            status=StudentStatus.ACTIVE,
        )

        # 为 student1 创建材料关联（有 raw 值）
        cls.summary1 = IdeologicalReportSummary.objects.create(
            student=cls.student1,
            reported_total_count=8,
            calculated_date_count=4,
        )
        IdeologicalReport.objects.create(
            student=cls.student1,
            sequence_number=1,
            submitted_at=date(2025, 6, 1),
            source_column_name="第1次思想汇报",
            is_active=True,
        )
        IdeologicalReport.objects.create(
            student=cls.student1,
            sequence_number=2,
            submitted_at=date(2025, 9, 1),
            source_column_name="第2次思想汇报",
            is_active=True,
        )
        # 创建一条失效记录，验证详情不展示
        IdeologicalReport.objects.create(
            student=cls.student1,
            sequence_number=3,
            submitted_at=date(2025, 12, 1),
            source_column_name="第3次思想汇报（已回滚）",
            is_active=False,
        )

        # 为 student4 创建只有计算值的汇总（reported_total_count=None）
        cls.summary4 = IdeologicalReportSummary.objects.create(
            student=cls.student4,
            reported_total_count=None,
            calculated_date_count=12,
        )
        IdeologicalReport.objects.create(
            student=cls.student4,
            sequence_number=1,
            submitted_at=date(2025, 3, 1),
            source_column_name="第1次思想汇报",
            is_active=True,
        )

        # 管理员用户
        cls.viewer = AdminUser.objects.create_user(
            username="viewer01",
            password="testpass123",
            role=AdminRole.VIEWER_ADMIN,
            display_name="查询管理员",
        )
        cls.data_admin = AdminUser.objects.create_user(
            username="data01",
            password="testpass123",
            role=AdminRole.DATA_ADMIN,
            display_name="数据管理员",
        )


# ──────────────────────────────────────────────
# 1. 登录成功和失败
# ──────────────────────────────────────────────
class AdminLoginTests(AdminQueryTestCase):
    def test_login_success_redirects_to_student_list(self) -> None:
        """管理员登录成功跳转到学生列表页。"""
        response = self.client.post(
            reverse("accounts:admin_login"),
            {"username": "viewer01", "password": "testpass123"},
        )
        self.assertRedirects(response, reverse("students:admin_student_list"))

    def test_login_success_writes_audit_log(self) -> None:
        """登录成功写入 audit log。"""
        self.client.post(
            reverse("accounts:admin_login"),
            {"username": "viewer01", "password": "testpass123"},
        )
        self.assertTrue(
            OperationLog.objects.filter(action="admin_login", operator=self.viewer).exists()
        )

    def test_login_failure_shows_error(self) -> None:
        """密码错误返回登录页并含错误提示。"""
        response = self.client.post(
            reverse("accounts:admin_login"),
            {"username": "viewer01", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "用户名或密码错误")

    def test_login_failure_no_audit_log(self) -> None:
        """登录失败不写审计日志。"""
        self.client.post(
            reverse("accounts:admin_login"),
            {"username": "viewer01", "password": "wrongpassword"},
        )
        self.assertFalse(
            OperationLog.objects.filter(action="admin_login").exists()
        )


# ──────────────────────────────────────────────
# 2 & 3. POST 退出清除 Session；GET 退出不作为正式入口
# ──────────────────────────────────────────────
class AdminLogoutTests(AdminQueryTestCase):
    def setUp(self) -> None:
        self.client.login(username="viewer01", password="testpass123")

    def test_post_logout_clears_session(self) -> None:
        """POST 退出清除认证 Session。"""
        session = self.client.session
        session["student_id"] = self.student1.pk
        session.save()
        response = self.client.post(reverse("accounts:admin_logout"))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("student_id", self.client.session)
        # 退出后不应再能访问受保护页面
        list_response = self.client.get(reverse("students:admin_student_list"))
        self.assertNotEqual(list_response.status_code, 200)

    def test_post_logout_writes_audit_log(self) -> None:
        """POST 退出写入审计日志。"""
        self.client.post(reverse("accounts:admin_logout"))
        self.assertTrue(
            OperationLog.objects.filter(action="admin_logout", operator=self.viewer).exists()
        )

    def test_get_logout_not_accepted(self) -> None:
        """GET 退出不作为正式入口（返回 405 Method Not Allowed）。"""
        response = self.client.get(reverse("accounts:admin_logout"))
        self.assertEqual(response.status_code, 405)


# ──────────────────────────────────────────────
# 4. 未登录不能访问列表和详情
# ──────────────────────────────────────────────
class UnauthenticatedAccessTests(AdminQueryTestCase):
    def test_anonymous_cannot_access_list(self) -> None:
        """未登录访问学生列表跳转登录页。"""
        response = self.client.get(reverse("students:admin_student_list"))
        self.assertNotEqual(response.status_code, 200)

    def test_anonymous_cannot_access_detail(self) -> None:
        """未登录访问学生详情跳转登录页。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student1.pk})
        )
        self.assertNotEqual(response.status_code, 200)


# ──────────────────────────────────────────────
# 5 & 6. viewer 和 data_admin 权限矩阵
# ──────────────────────────────────────────────
class ViewerPermissionTests(AdminQueryTestCase):
    def setUp(self) -> None:
        self.client.login(username="viewer01", password="testpass123")

    def test_viewer_can_access_student_list(self) -> None:
        """viewer 可访问学生列表。"""
        response = self.client.get(reverse("students:admin_student_list"))
        self.assertEqual(response.status_code, 200)

    def test_viewer_can_access_student_detail(self) -> None:
        """viewer 可访问学生详情。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student1.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_access_import_upload(self) -> None:
        """冻结导入契约要求viewer不能访问Excel上传入口。"""
        response = self.client.get(reverse("imports:upload"))
        self.assertEqual(response.status_code, 403)


class DataAdminPermissionTests(AdminQueryTestCase):
    def setUp(self) -> None:
        self.client.login(username="data01", password="testpass123")

    def test_data_admin_can_access_student_list(self) -> None:
        """data_admin 可访问学生列表。"""
        response = self.client.get(reverse("students:admin_student_list"))
        self.assertEqual(response.status_code, 200)

    def test_data_admin_can_access_student_detail(self) -> None:
        """data_admin 可访问学生详情。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student1.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_data_admin_can_access_import_upload(self) -> None:
        """data_admin 可访问 Excel 导入上传页。"""
        response = self.client.get(reverse("imports:upload"))
        self.assertEqual(response.status_code, 200)


# ──────────────────────────────────────────────
# 7. 五类筛选均有效
# ──────────────────────────────────────────────
class FilterTests(AdminQueryTestCase):
    def setUp(self) -> None:
        self.client.login(username="viewer01", password="testpass123")

    def test_filter_by_name_fuzzy(self) -> None:
        """姓名模糊筛选。"""
        response = self.client.get(reverse("students:admin_student_list"), {"name": "张"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "张三")
        self.assertNotContains(response, "李四")
        self.assertNotContains(response, "王五")

    def test_filter_by_student_number_fuzzy(self) -> None:
        """学号模糊筛选。"""
        response = self.client.get(
            reverse("students:admin_student_list"), {"student_number": "20260001"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "张三")
        self.assertNotContains(response, "李四")

    def test_filter_by_branch_exact(self) -> None:
        """支部精确筛选。"""
        response = self.client.get(
            reverse("students:admin_student_list"), {"branch": str(self.branch_a.pk)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "张三")
        self.assertContains(response, "王五")
        self.assertNotContains(response, "李四")

    def test_filter_by_stage_exact(self) -> None:
        """发展阶段精确筛选。"""
        response = self.client.get(
            reverse("students:admin_student_list"), {"stage": "PROBATIONARY"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "李四")
        self.assertNotContains(response, "张三")

    def test_filter_by_status_exact(self) -> None:
        """学生状态精确筛选。"""
        response = self.client.get(
            reverse("students:admin_student_list"), {"status": "inactive"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "王五")
        self.assertNotContains(response, "张三")

    def test_filters_can_be_combined(self) -> None:
        """多条件组合筛选。"""
        response = self.client.get(
            reverse("students:admin_student_list"),
            {"name": "张", "branch": str(self.branch_a.pk), "stage": "ACTIVIST"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "张三")


# ──────────────────────────────────────────────
# 8. 非法 branch/stage 不返回 500
# ──────────────────────────────────────────────
class InvalidFilterTests(AdminQueryTestCase):
    def setUp(self) -> None:
        self.client.login(username="viewer01", password="testpass123")

    def test_invalid_branch_id_returns_200(self) -> None:
        """非法支部 ID 返回200、错误提示及空结果。"""
        response = self.client.get(
            reverse("students:admin_student_list"), {"branch": "not_a_number"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        self.assertContains(response, "党支部筛选值无效")

    def test_invalid_branch_id_nonexistent_returns_200(self) -> None:
        """不存在的支部ID不产生500。"""
        response = self.client.get(
            reverse("students:admin_student_list"), {"branch": "99999"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_invalid_stage_returns_200(self) -> None:
        """非法阶段值不产生 500。"""
        response = self.client.get(
            reverse("students:admin_student_list"), {"stage": "INVALID_STAGE"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        self.assertContains(response, "发展阶段筛选值无效")

    def test_invalid_status_returns_200(self) -> None:
        """非法状态值不产生 500。"""
        response = self.client.get(
            reverse("students:admin_student_list"), {"status": "INVALID_STATUS"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        self.assertContains(response, "学生状态筛选值无效")


# ──────────────────────────────────────────────
# 9. 翻页保留筛选条件
# ──────────────────────────────────────────────
class PaginationFilterPreservationTests(AdminQueryTestCase):
    def setUp(self) -> None:
        self.client.login(username="viewer01", password="testpass123")
        # 创建足够多的学生以触发固定20条分页
        for i in range(60):
            Student.objects.create(
                name=f"批量学生{i:03d}",
                student_number=f"B{50 + i:05d}",
                branch=self.branch_a,
                development_stage=DevelopmentStage.ACTIVIST,
                status=StudentStatus.ACTIVE,
            )

    def test_pagination_preserves_filters(self) -> None:
        """翻页链接保留筛选参数。"""
        response = self.client.get(
            reverse("students:admin_student_list"),
            {"name": "批量", "page": 2},
        )
        self.assertEqual(response.status_code, 200)
        # 翻页链接中应保留 name 参数
        self.assertContains(response, "name=")

    def test_pagination_is_fixed_at_twenty(self) -> None:
        response = self.client.get(reverse("students:admin_student_list"))
        self.assertEqual(response.context["page_obj"].paginator.per_page, 20)
        self.assertEqual(len(response.context["students"]), 20)

    def test_page_size_parameter_is_ignored(self) -> None:
        response = self.client.get(
            reverse("students:admin_student_list"), {"page_size": 100}
        )
        self.assertEqual(response.context["page_obj"].paginator.per_page, 20)
        self.assertEqual(len(response.context["students"]), 20)


# ──────────────────────────────────────────────
# 10. 列表展示冻结字段
# ──────────────────────────────────────────────
class ListFieldTests(AdminQueryTestCase):
    def setUp(self) -> None:
        self.client.login(username="viewer01", password="testpass123")

    def test_list_displays_all_required_fields(self) -> None:
        """列表展示：姓名、学号、支部、阶段、职务、状态、更新时间、详情入口。"""
        response = self.client.get(reverse("students:admin_student_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "张三")
        self.assertContains(response, "20260001")
        self.assertContains(response, "第一党支部")
        self.assertContains(response, "班长")
        # 应有详情链接
        detail_url = reverse("students:admin_student_detail", kwargs={"pk": self.student1.pk})
        self.assertContains(response, detail_url)


# ──────────────────────────────────────────────
# 11. 详情展示汇总原始值和计算值、统计来源
# ──────────────────────────────────────────────
class DetailFieldTests(AdminQueryTestCase):
    def setUp(self) -> None:
        self.client.login(username="viewer01", password="testpass123")

    # ── 原始值存在时 ──

    def test_detail_displays_reported_total_count_when_not_none(self) -> None:
        """reported_total_count 非 None 时展示 Excel 填报总篇数。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student1.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "8 篇")

    def test_detail_shows_excel_source_when_raw_not_none(self) -> None:
        """原始值存在时统计来源显示 Excel原始填报值。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student1.pk})
        )
        self.assertContains(response, "Excel原始填报值")

    def test_detail_also_shows_calculated_when_raw_exists(self) -> None:
        """管理员详情同时展示原始值和系统计算值，便于交叉核验。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student1.pk})
        )
        self.assertContains(response, "4 天")

    # ── 原始值为 None 时 ──

    def test_detail_displays_calculated_count_when_raw_is_none(self) -> None:
        """reported_total_count 为 None 时展示系统计算日期数。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student4.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "12 天")

    def test_detail_shows_system_source_when_raw_is_none(self) -> None:
        """原始值为 None 时统计来源显示系统计算。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student4.pk})
        )
        self.assertContains(response, "系统计算")

    # ── 0 不作为 None 处理 ──

    def test_detail_zero_raw_count_shows_zero_and_excel_source(self) -> None:
        """reported_total_count=0 时展示 0 篇且来源为 Excel，不回退到计算值。"""
        student_zero = Student.objects.create(
            name="零值测试",
            student_number="20260010",
            branch=self.branch_a,
            development_stage=DevelopmentStage.ACTIVIST,
            status=StudentStatus.ACTIVE,
        )
        IdeologicalReportSummary.objects.create(
            student=student_zero,
            reported_total_count=0,
            calculated_date_count=5,
        )
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": student_zero.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0 篇")
        self.assertContains(response, "Excel原始填报值")
        self.assertContains(response, "5 天")

    # ── 通用 ──

    def test_detail_displays_update_time(self) -> None:
        """详情展示最近更新时间。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student1.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "最近更新时间")


# ──────────────────────────────────────────────
# 11b. 思想汇报 is_active 过滤与排序
# ──────────────────────────────────────────────
class IdeologicalReportFilteringTests(AdminQueryTestCase):
    def setUp(self) -> None:
        self.client.login(username="viewer01", password="testpass123")

    def test_active_reports_are_listed_in_order(self) -> None:
        """有效思想汇报按 sequence_number 排序展示。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student1.pk})
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # 第1次应在第2次之前
        pos1 = content.find("第1次")
        pos2 = content.find("第2次")
        self.assertGreater(pos1, -1)
        self.assertGreater(pos2, -1)
        self.assertLess(pos1, pos2)

    def test_inactive_report_not_shown(self) -> None:
        """is_active=False 的思想汇报不在详情中展示。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student1.pk})
        )
        self.assertEqual(response.status_code, 200)
        # student1 有 sequence_number=3, is_active=False 的记录，不应展示
        self.assertNotContains(response, "第3次")
        self.assertNotContains(response, "已回滚")

    def test_detail_label_shows_active_records(self) -> None:
        """思想汇报明细区域标注为有效记录。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student1.pk})
        )
        self.assertContains(response, "有效记录")


# ──────────────────────────────────────────────
# 12. 关联材料缺失不报错
# ──────────────────────────────────────────────
class MissingMaterialsTests(AdminQueryTestCase):
    def setUp(self) -> None:
        self.client.login(username="viewer01", password="testpass123")

    def test_student_without_materials_returns_200(self) -> None:
        """无材料关联的学生详情页正常展示，不报错。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student3.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student3.name)


# ──────────────────────────────────────────────
# 13. 学生不存在返回 404
# ──────────────────────────────────────────────
class StudentNotFoundTests(AdminQueryTestCase):
    def setUp(self) -> None:
        self.client.login(username="viewer01", password="testpass123")

    def test_nonexistent_student_returns_404(self) -> None:
        """不存在的学生返回 404。"""
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": 99999})
        )
        self.assertEqual(response.status_code, 404)


# ──────────────────────────────────────────────
# 14. 查看详情写入 OperationLog
# ──────────────────────────────────────────────
class AuditLogOnDetailTests(AdminQueryTestCase):
    def setUp(self) -> None:
        self.client.login(username="viewer01", password="testpass123")

    def test_viewing_detail_writes_operation_log(self) -> None:
        """查看学生详情写入审计日志。"""
        self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student1.pk})
        )
        self.assertTrue(
            OperationLog.objects.filter(
                action="view_student_detail",
                target_type="student",
                target_id=str(self.student1.pk),
            ).exists()
        )


# ──────────────────────────────────────────────
# 空数据情况
# ──────────────────────────────────────────────
class EmptyDataTests(AdminQueryTestCase):
    def setUp(self) -> None:
        self.client.login(username="viewer01", password="testpass123")

    def test_filter_no_results_shows_empty_message(self) -> None:
        """筛选无结果展示空数据提示。"""
        response = self.client.get(
            reverse("students:admin_student_list"), {"name": "不存在的人"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "暂无学生数据")


# ══════════════════════════════════════════════════════════
# 统一权限接口测试
# ══════════════════════════════════════════════════════════
class UnifiedPermissionTests(TestCase):
    """验证 check_admin_role 和 Mixin 统一生效。"""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.viewer = AdminUser.objects.create_user(
            username="perm_viewer",
            password="testpass123",
            role=AdminRole.VIEWER_ADMIN,
        )
        cls.data_admin = AdminUser.objects.create_user(
            username="perm_data",
            password="testpass123",
            role=AdminRole.DATA_ADMIN,
        )
        cls.branch = PartyBranch.objects.create(code="P01", name="权限测试支部")
        cls.student = Student.objects.create(
            name="权限测试学生",
            student_number="P00001",
            branch=cls.branch,
            development_stage=DevelopmentStage.ACTIVIST,
            status=StudentStatus.ACTIVE,
        )

    # ── check_admin_role 工具函数 ──

    def test_check_admin_role_viewer_is_viewer(self) -> None:
        """viewer_admin 属于 VIEWER_ADMIN 角色。"""
        self.assertTrue(check_admin_role(self.viewer, AdminRole.VIEWER_ADMIN))

    def test_check_admin_role_viewer_is_not_data_admin(self) -> None:
        """viewer_admin 不属于 DATA_ADMIN 角色。"""
        self.assertFalse(check_admin_role(self.viewer, AdminRole.DATA_ADMIN))

    def test_check_admin_role_data_admin_is_both(self) -> None:
        """data_admin 同时符合 VIEWER_ADMIN 或 DATA_ADMIN 检查。"""
        self.assertTrue(
            check_admin_role(self.data_admin, AdminRole.VIEWER_ADMIN, AdminRole.DATA_ADMIN)
        )
        self.assertTrue(check_admin_role(self.data_admin, AdminRole.DATA_ADMIN))

    def test_check_admin_role_anonymous_returns_false(self) -> None:
        """匿名用户（无 role 属性）返回 False。"""
        from django.contrib.auth.models import AnonymousUser
        anon = AnonymousUser()
        self.assertFalse(check_admin_role(anon, AdminRole.VIEWER_ADMIN))

    def test_check_admin_role_inactive_returns_false(self) -> None:
        self.viewer.is_active = False
        self.assertFalse(check_admin_role(self.viewer, AdminRole.VIEWER_ADMIN))

    def test_check_admin_role_unknown_role_returns_false(self) -> None:
        self.viewer.role = "unknown_admin"
        self.assertFalse(check_admin_role(self.viewer, "unknown_admin"))

    # ── 类视图 Mixin 一致生效 ──

    def test_viewer_gets_200_on_list_with_mixin(self) -> None:
        """ViewerOrDataAdminRequiredMixin 对 viewer 放行列表。"""
        self.client.login(username="perm_viewer", password="testpass123")
        response = self.client.get(reverse("students:admin_student_list"))
        self.assertEqual(response.status_code, 200)

    def test_viewer_gets_200_on_detail_with_mixin(self) -> None:
        """ViewerOrDataAdminRequiredMixin 对 viewer 放行详情。"""
        self.client.login(username="perm_viewer", password="testpass123")
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_data_admin_gets_200_on_list_with_mixin(self) -> None:
        """ViewerOrDataAdminRequiredMixin 对 data_admin 放行。"""
        self.client.login(username="perm_data", password="testpass123")
        response = self.client.get(reverse("students:admin_student_list"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_redirected_with_mixin(self) -> None:
        """ViewerOrDataAdminRequiredMixin 对未登录用户跳转。"""
        response = self.client.get(reverse("students:admin_student_list"))
        self.assertNotEqual(response.status_code, 200)


# ══════════════════════════════════════════════════════════
# 审计 IP 测试
# ══════════════════════════════════════════════════════════
class AuditIPTests(TestCase):
    """验证 get_client_ip 在有无可信代理时的行为。"""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.audit_user = AdminUser.objects.create_user(
            username="audit_ip_user",
            password="testpass123",
            role=AdminRole.VIEWER_ADMIN,
        )

    def test_uses_remote_addr_when_no_trusted_proxies(self) -> None:
        """无 TRUSTED_PROXIES 设置时，直接使用 REMOTE_ADDR，忽略 X-Forwarded-For。"""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.100"
        request.META["HTTP_X_FORWARDED_FOR"] = "10.0.0.1, 10.0.0.2"
        request.user = AdminUser(
            username="test", role=AdminRole.VIEWER_ADMIN
        )
        ip = get_client_ip(request)
        self.assertEqual(ip, "192.168.1.100")

    @override_settings(TRUSTED_PROXIES=["10.0.0.0/8"])
    def test_uses_x_forwarded_for_when_trusted_proxies_set(self) -> None:
        """有 TRUSTED_PROXIES 配置时，信任 X-Forwarded-For 最左 IP。"""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        request.META["REMOTE_ADDR"] = "10.0.0.1"
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.5, 10.0.0.1"
        request.user = AdminUser(
            username="test", role=AdminRole.VIEWER_ADMIN
        )
        ip = get_client_ip(request)
        self.assertEqual(ip, "203.0.113.5")

    @override_settings(TRUSTED_PROXIES=["10.0.0.0/8"])
    def test_ignores_forwarded_for_from_untrusted_remote(self) -> None:
        from django.test import RequestFactory
        request = RequestFactory().get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.100"
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.5"
        self.assertEqual(get_client_ip(request), "192.168.1.100")

    def test_falls_back_to_remote_addr_when_no_header(self) -> None:
        """无 X-Forwarded-For 头时始终使用 REMOTE_ADDR。"""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.200"
        request.user = AdminUser(
            username="test", role=AdminRole.VIEWER_ADMIN
        )
        ip = get_client_ip(request)
        self.assertEqual(ip, "192.168.1.200")

    def test_audit_log_records_ip_on_login(self) -> None:
        """登录审计日志记录 IP 地址。"""
        self.client.post(
            reverse("accounts:admin_login"),
            {"username": "audit_ip_user", "password": "testpass123"},
            REMOTE_ADDR="192.168.1.50",
        )
        log = OperationLog.objects.filter(action="admin_login").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.ip_address, "192.168.1.50")

    def test_audit_log_records_ip_on_detail_view(self) -> None:
        """查看详情审计日志记录 IP 地址。"""
        from apps.accounts.models import AdminUser
        from apps.students.models import PartyBranch, Student, StudentStatus, DevelopmentStage
        # 需要预创建数据
        user = AdminUser.objects.create_user(
            username="iptest",
            password="testpass123",
            role=AdminRole.VIEWER_ADMIN,
        )
        branch = PartyBranch.objects.create(code="IPT", name="IP测试支部")
        student = Student.objects.create(
            name="IP测试学生",
            student_number="IP0001",
            branch=branch,
            development_stage=DevelopmentStage.ACTIVIST,
            status=StudentStatus.ACTIVE,
        )
        self.client.login(username="iptest", password="testpass123")
        self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": student.pk}),
            REMOTE_ADDR="10.20.30.40",
        )
        log = OperationLog.objects.filter(action="view_student_detail").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.ip_address, "10.20.30.40")
