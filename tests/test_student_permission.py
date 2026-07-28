from django.test import TestCase
from django.urls import reverse

from apps.students.models import DevelopmentStage, PartyBranch, Student, StudentStatus


class StudentPermissionAndSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.branch = PartyBranch.objects.create(code="PERM_TEST", name="权限会话测试支部")
        cls.student_a = Student.objects.create(
            name="吴九",
            student_number="S20260201",
            branch=cls.branch,
            development_stage=DevelopmentStage.ACTIVIST,
            status=StudentStatus.ACTIVE,
        )
        cls.student_b = Student.objects.create(
            name="郑十",
            student_number="S20260202",
            branch=cls.branch,
            development_stage=DevelopmentStage.FULL_MEMBER,
            status=StudentStatus.ACTIVE,
        )
        cls.login_url = reverse("accounts:student_login")
        cls.logout_url = reverse("accounts:student_logout")
        cls.profile_url = reverse("students:student_profile")
        cls.admin_list_url = reverse("students:admin_student_list")
        cls.admin_detail_url = reverse("students:admin_student_detail", kwargs={"pk": cls.student_a.pk})

    def _login_as(self, student: Student):
        return self.client.post(
            self.login_url, {"name": student.name, "student_number": student.student_number}
        )

    def _logout(self):
        return self.client.get(self.logout_url)

    def test_scenario_06_anonymous_profile_redirects(self) -> None:
        """场景 6：未登录直接访问个人信息页 → 跳转登录页"""
        response = self.client.get(self.profile_url)
        self.assertRedirects(response, self.login_url, fetch_redirect_response=False)

    def test_scenario_07_logout_clears_session(self) -> None:
        """场景 7：点击退出登录 → Session 中的 student_id 被清除"""
        self._login_as(self.student_a)
        self.assertEqual(self.client.session.get("student_id"), self.student_a.id)
        response = self._logout()
        self.assertRedirects(response, self.login_url, fetch_redirect_response=False)
        self.assertIsNone(self.client.session.get("student_id"))

    def test_scenario_08_profile_after_logout_redirects(self) -> None:
        """场景 8：退出后访问个人信息页 → 跳转登录页"""
        self._login_as(self.student_a)
        self._logout()
        profile_response = self.client.get(self.profile_url)
        self.assertRedirects(profile_response, self.login_url, fetch_redirect_response=False)

    def test_scenario_09_url_forged_student_id_ignored(self) -> None:
        """场景 9：通过 URL 伪造 student_id → 不被接受（实际仍用 Session 对应的学生）"""
        self._login_as(self.student_a)
        forged_url = f"{self.profile_url}?student_id={self.student_b.pk}"
        response = self.client.get(forged_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_student_id"], self.student_a.pk)
        self.assertEqual(response.context["student"].pk, self.student_a.pk)
        self.assertNotEqual(response.context["current_student_id"], self.student_b.pk)

    def test_scenario_10_student_blocked_on_admin_urls(self) -> None:
        """场景 10：学生访问管理员 URL → 返回 403"""
        self._login_as(self.student_a)
        list_response = self.client.get(self.admin_list_url)
        detail_response = self.client.get(self.admin_detail_url)
        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(detail_response.status_code, 403)
