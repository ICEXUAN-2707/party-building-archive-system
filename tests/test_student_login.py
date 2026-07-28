from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from apps.students.models import DevelopmentStage, PartyBranch, Student, StudentStatus


class StudentLoginFullCoverageTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.branch = PartyBranch.objects.create(code="FULL_LOGIN", name="完整登录测试支部")
        cls.student = Student.objects.create(
            name="孙七",
            student_number="S20260101",
            branch=cls.branch,
            development_stage=DevelopmentStage.ACTIVIST,
            status=StudentStatus.ACTIVE,
        )
        cls.other_student = Student.objects.create(
            name="周八",
            student_number="S20260102",
            branch=cls.branch,
            development_stage=DevelopmentStage.PROBATIONARY,
            status=StudentStatus.ACTIVE,
        )
        cls.login_url = reverse("accounts:student_login")
        cls.logout_url = reverse("accounts:student_logout")
        cls.profile_url = reverse("students:student_profile")
        cls.admin_list_url = reverse("students:admin_student_list")
        cls.admin_detail_url = reverse("students:admin_student_detail", kwargs={"pk": cls.student.pk})
        cls.correct_payload = {"name": "孙七", "student_number": "S20260101"}
        cls.wrong_payload = {"name": "错误姓名", "student_number": "S99999999"}
        cls.empty_name_payload = {"name": "", "student_number": "S20260101"}
        cls.empty_number_payload = {"name": "孙七", "student_number": ""}
        cls.generic_error = "姓名或学号不匹配"
        cls.lockout_error = "登录失败次数过多，请 5 分钟后再试"

    def _login_correct(self):
        return self.client.post(self.login_url, self.correct_payload)

    def _logout(self):
        return self.client.get(self.logout_url)

    # ====== 场景 1-5：登录基础 ======

    def test_scenario_01_correct_credentials_login(self) -> None:
        """场景 1：正确姓名+学号 → 跳转个人信息页，Session 有 student_id"""
        response = self._login_correct()
        self.assertRedirects(response, self.profile_url, fetch_redirect_response=False)
        self.assertEqual(self.client.session.get("student_id"), self.student.id)

    def test_scenario_02_empty_name(self) -> None:
        """场景 2：姓名为空 → 表单校验不通过"""
        response = self.client.post(self.login_url, self.empty_name_payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.generic_error)
        self.assertIsNone(self.client.session.get("student_id"))

    def test_scenario_03_empty_student_number(self) -> None:
        """场景 3：学号为空 → 表单校验不通过"""
        response = self.client.post(self.login_url, self.empty_number_payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.generic_error)
        self.assertIsNone(self.client.session.get("student_id"))

    def test_scenario_04_mismatch_unified_error(self) -> None:
        """场景 4：组合不匹配 → 统一错误提示，不暴露具体字段"""
        wrong_name_resp = self.client.post(
            self.login_url, {"name": "错名", "student_number": "S20260101"}
        )
        wrong_number_resp = self.client.post(
            self.login_url, {"name": "孙七", "student_number": "S00000000"}
        )
        for resp in [wrong_name_resp, wrong_number_resp]:
            self.assertEqual(resp.status_code, 200)
            self.assertContains(resp, self.generic_error)
            content = resp.content.decode("utf-8")
            self.assertNotIn("姓名错误", content)
            self.assertNotIn("学号错误", content)
            form = resp.context["form"]
            self.assertEqual(len(form.errors.get("name", [])), 0)
            self.assertEqual(len(form.errors.get("student_number", [])), 0)
            self.assertGreaterEqual(len(form.non_field_errors()), 1)

    def test_scenario_05_profile_after_login(self) -> None:
        """场景 5：登录成功访问个人信息页 → 正常显示"""
        self._login_correct()
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/student_profile.html")
        self.assertEqual(response.context["current_student_id"], self.student.id)
        self.assertEqual(response.context["student"].pk, self.student.pk)

    # ====== 场景 11-13：失败限流 ======

    def test_scenario_11_five_failures_trigger_lockout(self) -> None:
        """场景 11：连续 5 次失败 → 触发限制提示"""
        for i in range(1, 6):
            response = self.client.post(self.login_url, self.wrong_payload)
            if i < 5:
                self.assertContains(response, self.generic_error)
                self.assertNotContains(response, self.lockout_error)
            else:
                self.assertContains(response, self.lockout_error)

    def test_scenario_12_lockout_skips_database_query(self) -> None:
        """场景 12：限制期间 → 不执行数据库查询"""
        start_ts = 1_700_100_000.0
        with patch("apps.accounts.views.time.time", return_value=start_ts):
            for _ in range(5):
                self.client.post(self.login_url, self.wrong_payload)
        fake_filter = MagicMock(return_value=Student.objects.none())
        with patch("apps.accounts.views.time.time", return_value=start_ts + 30), patch(
            "apps.students.models.Student.objects.filter", side_effect=fake_filter
        ):
            self.client.post(self.login_url, self.correct_payload)
        fake_filter.assert_not_called()
        session = self.client.session
        self.assertIsNotNone(session.get("_student_login_locked_until"))

    def test_scenario_13_success_resets_counter(self) -> None:
        """场景 13：登录成功后失败计数归零"""
        for _ in range(4):
            self.client.post(self.login_url, self.wrong_payload)
        self.assertEqual(self.client.session.get("_student_login_failed_count"), 4)
        self._login_correct()
        self.assertIsNone(self.client.session.get("_student_login_failed_count"))
        self.assertIsNone(self.client.session.get("_student_login_locked_until"))
        self._logout()
        for i in range(1, 6):
            response = self.client.post(self.login_url, self.wrong_payload)
            if i < 5:
                self.assertNotContains(response, self.lockout_error)
            else:
                self.assertContains(response, self.lockout_error)
