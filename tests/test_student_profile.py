from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.materials.models import (
    ApplicationRecord,
    IdeologicalReport,
    IdeologicalReportSummary,
)
from apps.students.models import DevelopmentStage, PartyBranch, Student

class StudentProfileTestCase(TestCase):
    """学生个人档案只读页面单元测试，覆盖返工单用例 1-10。"""

    def setUp(self):
        self.branch = PartyBranch.objects.create(code="PROFILE", name="档案测试支部")
        self.student_a = Student.objects.create(
            name="张三",
            student_number="2026001",
            development_stage=DevelopmentStage.ACTIVIST,
            branch=self.branch,
        )
        self.student_b = Student.objects.create(
            name="李四",
            student_number="2026002",
            development_stage=DevelopmentStage.FULL_MEMBER,
            branch=self.branch,
        )
        self.profile_url = reverse("students:student_profile")
        self.login_url = reverse("accounts:student_login")

    def _login(self, student):
        session = self.client.session
        session["student_id"] = student.pk
        session.save()

    # 用例1：匿名访问个人页被重定向到登录页
    def test_anonymous_redirected_to_login(self):
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res["Location"], self.login_url)

    # 用例2：登录学生只看到本人姓名和学号
    def test_logged_in_sees_own_info_only(self):
        self._login(self.student_a)
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["student"].pk, self.student_a.pk)
        self.assertContains(res, "张三")
        self.assertContains(res, "2026001")
        self.assertNotContains(res, "李四")
        self.assertNotContains(res, "2026002")

    # 用例3：GET、POST 和 URL 参数均无法切换学生
    def test_get_post_url_cannot_switch_student(self):
        self._login(self.student_a)
        res_get = self.client.get(f"{self.profile_url}?student_id={self.student_b.pk}")
        self.assertEqual(res_get.context["student"].pk, self.student_a.pk)
        self.assertNotContains(res_get, "李四")
        res_post = self.client.post(self.profile_url, {"student_id": self.student_b.pk})
        self.assertEqual(res_post.context["student"].pk, self.student_a.pk)
        self.assertNotContains(res_post, "李四")

    # 用例4：申请记录存在和缺失
    def test_application_record_present_and_missing(self):
        ApplicationRecord.objects.create(student=self.student_a, applied_at=date(2025, 3, 1))
        self._login(self.student_a)
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, 200)
        self.assertIsNotNone(res.context["application_record"])
        self.assertContains(res, "2025年3月1日")
        # 切换到无申请记录的学生
        self._login(self.student_b)
        res2 = self.client.get(self.profile_url)
        self.assertEqual(res2.status_code, 200)
        self.assertIsNone(res2.context["application_record"])
        self.assertContains(res2, "暂无入党申请记录")

    # 用例5：学生页主数字始终与当前有效明细数量一致
    def test_report_count_uses_active_details_regardless_of_summary_values(self):
        cases = [(5, True), (0, False), (None, False)]
        for total, expect_mismatch in cases:
            with self.subTest(total=total):
                student = Student.objects.create(
                    name=f"汇总学生{total}",
                    student_number=f"SUM{total}",
                    development_stage=DevelopmentStage.ACTIVIST,
                    branch=self.branch,
                )
                IdeologicalReportSummary.objects.create(
                    student=student,
                    reported_total_count=total,
                    calculated_date_count=5,
                )
                self._login(student)
                res = self.client.get(self.profile_url)
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.context["report_count"], 0)
                self.assertEqual(res.context["report_count_mismatch"], expect_mismatch)

    # 用例6：没有有效明细时不使用汇总表中的旧计算值
    def test_none_total_count_does_not_replace_active_detail_count(self):
        IdeologicalReportSummary.objects.create(
            student=self.student_a,
            reported_total_count=None,
            calculated_date_count=5,
        )
        self._login(self.student_a)
        res = self.client.get(self.profile_url)
        self.assertEqual(res.context["report_count"], 0)
        self.assertContains(res, "当前有效思想汇报：0篇")

    def test_reported_four_with_three_details_shows_three_and_mismatch_warning(self):
        IdeologicalReportSummary.objects.create(
            student=self.student_a,
            reported_total_count=4,
            calculated_date_count=3,
        )
        for sequence in (1, 2, 3):
            IdeologicalReport.objects.create(
                student=self.student_a,
                sequence_number=sequence,
                submitted_at=date(2025, sequence, 1),
                source_column_name=f"第{sequence}次思想汇报",
                is_active=True,
            )

        self._login(self.student_a)
        res = self.client.get(self.profile_url)

        self.assertEqual(res.context["report_count"], 3)
        self.assertContains(res, "当前有效思想汇报：3篇")
        self.assertContains(res, "Excel填报总篇数为4篇")
        self.assertContains(res, "当前有效明细3篇不一致")

    # 用例7：只显示 is_active=True 的明细
    def test_only_active_reports_displayed(self):
        IdeologicalReport.objects.create(
            student=self.student_a, sequence_number=1, submitted_at=date(2025, 1, 1),
            source_column_name="第1次思想汇报", is_active=True,
        )
        IdeologicalReport.objects.create(
            student=self.student_a, sequence_number=2, submitted_at=date(2025, 2, 1),
            source_column_name="第2次思想汇报", is_active=False,
        )
        self._login(self.student_a)
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, 200)
        seqs = [r.sequence_number for r in res.context["idea_reports"]]
        self.assertEqual(seqs, [1])
        self.assertContains(res, "第1次思想汇报")
        self.assertNotContains(res, "第2次思想汇报")
        self.assertContains(res, "2025年1月1日")

    # 用例8：明细按真实 sequence_number 排序和标号
    def test_reports_ordered_by_sequence_number(self):
        for seq in [3, 1, 2]:
            IdeologicalReport.objects.create(
                student=self.student_a, sequence_number=seq,
                submitted_at=date(2025, seq, 1),
                source_column_name=f"第{seq}次思想汇报", is_active=True,
            )
        self._login(self.student_a)
        res = self.client.get(self.profile_url)
        seqs = [r.sequence_number for r in res.context["idea_reports"]]
        self.assertEqual(seqs, [1, 2, 3])
        content = res.content.decode()
        self.assertLess(content.index("第1次思想汇报"), content.index("第2次思想汇报"))
        self.assertLess(content.index("第2次思想汇报"), content.index("第3次思想汇报"))

    def test_profile_updated_at_uses_latest_system_record_time(self):
        """更新时间取系统记录时间，不得取业务提交日期。"""
        now = timezone.now().replace(second=0, microsecond=0)
        student_time = now - timedelta(days=3)
        application_time = now - timedelta(days=2)
        summary_time = now - timedelta(days=1)
        report_time = now

        application = ApplicationRecord.objects.create(
            student=self.student_a,
            applied_at=date(2019, 1, 1),
        )
        summary = IdeologicalReportSummary.objects.create(
            student=self.student_a,
            reported_total_count=1,
            calculated_date_count=1,
        )
        report = IdeologicalReport.objects.create(
            student=self.student_a,
            sequence_number=1,
            submitted_at=date(2020, 1, 1),
            source_column_name="第1次思想汇报",
            is_active=True,
        )
        Student.objects.filter(pk=self.student_a.pk).update(updated_at=student_time)
        ApplicationRecord.objects.filter(pk=application.pk).update(updated_at=application_time)
        IdeologicalReportSummary.objects.filter(pk=summary.pk).update(updated_at=summary_time)
        IdeologicalReport.objects.filter(pk=report.pk).update(created_at=report_time)

        self._login(self.student_a)
        res = self.client.get(self.profile_url)

        self.assertEqual(res.context["profile_updated_at"], report_time)
        local_report_time = timezone.localtime(report_time)
        expected_time = (
            f"{local_report_time.year}年{local_report_time.month}月{local_report_time.day}日 "
            f"{local_report_time:%H:%M}"
        )
        self.assertContains(res, expected_time)
        self.assertNotContains(res, "2020年1月1日 00:00")

    def test_profile_updated_at_falls_back_to_student_updated_at(self):
        self._login(self.student_a)
        res = self.client.get(self.profile_url)
        self.assertEqual(res.context["profile_updated_at"], self.student_a.updated_at)
        self.assertContains(res, "最近更新时间")

    # 用例9：无汇总、无明细时页面正常
    def test_empty_summary_and_reports_renders(self):
        self._login(self.student_a)
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["report_count"], 0)
        self.assertFalse(res.context["report_count_mismatch"])
        self.assertEqual(list(res.context["idea_reports"]), [])
        self.assertContains(res, "暂无有效思想汇报")
        self.assertContains(res, "暂无入党申请记录")

    # 用例10：无效 Session 不返回 500
    def test_invalid_session_does_not_500(self):
        session = self.client.session
        session["student_id"] = 99999999  # 不存在的主键
        session.save()
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res["Location"], self.login_url)
        self.assertNotIn("student_id", self.client.session)
