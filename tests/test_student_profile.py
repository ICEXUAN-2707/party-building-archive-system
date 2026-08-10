from django.test import TestCase
from django.urls import reverse
from apps.students.models import Student, PartyBranch

class StudentProfileTestCase(TestCase):
    def setUp(self):
        # 先创建党支部
        self.branch = PartyBranch.objects.create(name="第一学生党支部")

        # 创建测试学生
        self.test_student = Student.objects.create(
            name="张三",
            student_number="2026001",
            development_stage="ACTIVIST",
            branch=self.branch
        )
        self.other_student = Student.objects.create(
            name="李四",
            student_number="2026002",
            development_stage="FULL_MEMBER",
            branch=self.branch
        )

        self.profile_url = reverse("student-profile")

    def test_page_normal_render(self):
        """页面正常渲染，上下文学生数据正确"""
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["student"].id, self.test_student.id)

    def test_empty_relation_no_error(self):
        """无关联数据页面不抛异常"""
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context["application_records"]), 0)
        self.assertEqual(len(res.context["idea_reports"]), 0)

    def test_param_cannot_switch_student(self):
        """URL参数无法切换展示其他学生"""
        res = self.client.get(f"{self.profile_url}?student_id={self.other_student.id}")
        self.assertEqual(res.context["student"].id, self.test_student.id)
