from django.test import TestCase
from django.urls import reverse
from apps.students.models import Student


class StudentFullFlowTestCase(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            name="测试学生",
            student_number="2026010"
        )
        self.login_url = reverse("accounts:student_login")
        self.profile_url = reverse("students:student_profile")
        self.logout_url = reverse("accounts:student_logout")

    def test_full_flow_login_profile_logout(self):
        # 1. 登录写入session
        login_data = {
            "name": self.student.name,
            "student_number": self.student.student_number
        }
        self.client.post(self.login_url, login_data)
        self.assertEqual(self.client.session["student_id"], self.student.id)

        # 2. 访问个人页正常
        res_profile = self.client.get(self.profile_url)
        self.assertEqual(res_profile.status_code, 200)

        # 3. GET退出返回405，仅允许POST
        res_get_logout = self.client.get(self.logout_url)
        self.assertEqual(res_get_logout.status_code, 405)

        # 4. POST退出仅清除student_id，跳转登录
        res_logout = self.client.post(self.logout_url)
        self.assertRedirects(res_logout, self.login_url)
        self.assertNotIn("student_id", self.client.session)

        # 5. 退出后再次访问个人页被拦截
        res_after_logout = self.client.get(self.profile_url)
        self.assertRedirects(res_after_logout, self.login_url)
