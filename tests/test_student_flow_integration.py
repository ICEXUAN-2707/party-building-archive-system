from django.test import TestCase
from django.urls import reverse

from apps.students.models import DevelopmentStage, PartyBranch, Student

class StudentFullFlowTestCase(TestCase):
    """学生端真实 Session 联调测试，覆盖返工单用例 11-12 及完整登录退出流程。"""

    def setUp(self):
        self.branch = PartyBranch.objects.create(code="FLOW", name="联调测试支部")
        self.student = Student.objects.create(
            name="测试学生",
            student_number="2026010",
            development_stage=DevelopmentStage.ACTIVIST,
            branch=self.branch,
        )
        self.login_url = reverse("accounts:student_login")
        self.logout_url = reverse("accounts:student_logout")
        self.profile_url = reverse("students:student_profile")

    def test_full_flow_login_profile_logout(self):
        # 1. 登录写入 session 并跳转个人页
        res_login = self.client.post(
            self.login_url,
            {"name": "测试学生", "student_number": "2026010"},
        )
        self.assertEqual(res_login.status_code, 302)
        self.assertEqual(res_login["Location"], self.profile_url)
        self.assertEqual(self.client.session["student_id"], self.student.pk)

        # 2. 访问个人页正常，展示本人
        res_profile = self.client.get(self.profile_url)
        self.assertEqual(res_profile.status_code, 200)
        self.assertContains(res_profile, "测试学生")
        self.assertContains(res_profile, "2026010")

        # 3. GET 退出返回 405，仅允许 POST
        self.assertEqual(self.client.get(self.logout_url).status_code, 405)

        # 4. POST 退出仅清除 student_id 并跳转登录
        res_logout = self.client.post(self.logout_url)
        self.assertEqual(res_logout.status_code, 302)
        self.assertEqual(res_logout["Location"], self.login_url)
        self.assertNotIn("student_id", self.client.session)

        # 5. 退出后再访问个人页被拦截
        res_after = self.client.get(self.profile_url)
        self.assertEqual(res_after.status_code, 302)
        self.assertEqual(res_after["Location"], self.login_url)

    # 用例11：页面退出表单使用正确 URL 和 POST 方法
    def test_profile_logout_form_uses_post_and_correct_url(self):
        self.client.post(
            self.login_url,
            {"name": "测试学生", "student_number": "2026010"},
        )
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'method="post"')
        self.assertContains(res, f'action="{self.logout_url}"')

    # 用例12：匿名用户不能通过本 PR 的任何管理员路由读取学生数据
    def test_anonymous_cannot_read_student_data_via_admin_routes(self):
        Student.objects.create(
            name="特征学生甲",
            student_number="LEAK001",
            development_stage=DevelopmentStage.PROBATIONARY,
            branch=self.branch,
        )
        admin_urls = [
            reverse("students:admin_student_list"),
            reverse("students:admin_student_detail", kwargs={"pk": 1}),
        ]
        for url in admin_urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                # 占位页不返回真实学生数据
                self.assertNotContains(res, "特征学生甲")
                self.assertNotContains(res, "LEAK001")
