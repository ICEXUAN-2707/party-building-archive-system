from django.test import TestCase
from django.urls import reverse
from apps.students.models import Student, ApplicationRecord, IdeologicalReport


class StudentProfileTestCase(TestCase):
    def setUp(self):
        # 构建测试学生
        self.student = Student.objects.create(
            name="张三",
            student_number="2026001",
            development_stage="ACTIVIST"
        )
        # 其他学生（用于越权校验）
        self.other_student = Student.objects.create(
            name="李四",
            student_number="2026002",
            development_stage="FULL_MEMBER"
        )
        # 入党申请记录（填报总数存在）
        self.app_record = ApplicationRecord.objects.create(
            student=self.student,
            applied_at="2026-01-10",
            reported_total_count=3
        )
        # 有效思想汇报
        self.report1 = IdeologicalReport.objects.create(
            student=self.student,
            sequence_number=1,
            submitted_at="2026-02-01",
            is_active=True
        )
        self.report2 = IdeologicalReport.objects.create(
            student=self.student,
            sequence_number=2,
            submitted_at="2026-03-01",
            is_active=True
        )
        # 失效汇报（不展示）
        self.report_invalid = IdeologicalReport.objects.create(
            student=self.student,
            sequence_number=3,
            submitted_at="2026-04-01",
            is_active=False
        )
        self.profile_url = reverse("students:student_profile")
        self.login_url = reverse("accounts:student_login")

    def test_anonymous_redirect_login(self):
        # 匿名访问重定向登录页
        res = self.client.get(self.profile_url)
        self.assertRedirects(res, self.login_url)

    def test_invalid_session_redirect(self):
        # Session存不存在的学生ID，清理并重定向，不500
        session = self.client.session
        session["student_id"] = 99999
        session.save()
        res = self.client.get(self.profile_url)
        self.assertRedirects(res, self.login_url)

    def test_login_only_see_self_data(self):
        # 登录学生只能查看自己信息，看不到他人
        session = self.client.session
        session["student_id"] = self.student.id
        session.save()
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["student"].id, self.student.id)
        # 总数读取填报值
        self.assertEqual(res.context["report_count"], 3)
        self.assertFalse(res.context["is_count_from_system"])
        # 只加载有效汇报，按序号排序
        self.assertEqual(len(res.context["report_list"]), 2)
        self.assertEqual(res.context["report_list"][0].sequence_number, 1)

    def test_no_application_use_system_count(self):
        # 删除申请记录，使用系统统计数量
        self.app_record.delete()
        session = self.client.session
        session["student_id"] = self.student.id
        session.save()
        res = self.client.get(self.profile_url)
        self.assertEqual(res.context["report_count"], 2)
        self.assertTrue(res.context["is_count_from_system"])

    def test_request_param_cannot_switch_student(self):
        # 请求参数无法切换身份，只能读取session学生
        session = self.client.session
        session["student_id"] = self.student.id
        session.save()
        res = self.client.get(f"{self.profile_url}?student_id={self.other_student.id}")
        self.assertEqual(res.context["student"].id, self.student.id)
