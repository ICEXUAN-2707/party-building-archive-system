from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from apps.students.models import DevelopmentStage, PartyBranch, Student, StudentStatus


class StudentLoginThrottleTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.branch = PartyBranch.objects.create(code="THROTTLE_TEST", name="限流测试支部")
        cls.student = Student.objects.create(
            name="节流测试生",
            student_number="ST20260009",
            branch=cls.branch,
            development_stage=DevelopmentStage.ACTIVIST,
            status=StudentStatus.ACTIVE,
        )
        cls.login_url = reverse("accounts:student_login")
        cls.profile_url = reverse("students:student_profile")
        cls.correct_payload = {"name": "节流测试生", "student_number": "ST20260009"}
        cls.wrong_payload = {"name": "错名", "student_number": "S00000000"}
        cls.empty_payload = {"name": "", "student_number": ""}
        cls.generic_error = "姓名或学号不匹配"
        cls.lockout_error = "登录失败次数过多，请 5 分钟后再试"

    def _post(self, payload):
        return self.client.post(self.login_url, payload)

    def test_first_four_failures_show_generic_error_not_lockout(self) -> None:
        for _ in range(4):
            response = self._post(self.wrong_payload)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, self.generic_error)
            self.assertNotContains(response, self.lockout_error)

    def test_fifth_failure_triggers_lockout_message(self) -> None:
        for _ in range(4):
            self._post(self.wrong_payload)
        fifth_response = self._post(self.wrong_payload)
        self.assertEqual(fifth_response.status_code, 200)
        self.assertContains(fifth_response, self.lockout_error)

    def test_lockout_period_blocks_correct_credentials(self) -> None:
        for _ in range(5):
            self._post(self.wrong_payload)
        response = self._post(self.correct_payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.lockout_error)
        self.assertIsNone(self.client.session.get("student_id"))

    def test_lockout_expires_after_five_minutes(self) -> None:
        start = 1_700_000_000.0
        with patch("apps.accounts.views.time.time", return_value=start):
            for _ in range(5):
                self._post(self.wrong_payload)
            response_during_lock = self._post(self.correct_payload)
            self.assertContains(response_during_lock, self.lockout_error)
            self.assertIsNone(self.client.session.get("student_id"))
        with patch("apps.accounts.views.time.time", return_value=start + 5 * 60 + 1):
            response_after_expiry = self._post(self.correct_payload)
            self.assertRedirects(response_after_expiry, self.profile_url, fetch_redirect_response=False)
            self.assertEqual(self.client.session.get("student_id"), self.student.id)

    def test_successful_login_resets_failure_counter(self) -> None:
        for _ in range(4):
            self._post(self.wrong_payload)
        self.assertEqual(self.client.session.get("_student_login_failed_count"), 4)
        reset_response = self._post(self.correct_payload)
        self.assertRedirects(reset_response, self.profile_url, fetch_redirect_response=False)
        self.assertIsNone(self.client.session.get("_student_login_failed_count"))
        self.assertIsNone(self.client.session.get("_student_login_locked_until"))
        self.client.get(reverse("accounts:student_logout"))
        for i in range(1, 6):
            response = self._post(self.wrong_payload)
            if i < 5:
                self.assertNotContains(response, self.lockout_error)
            else:
                self.assertContains(response, self.lockout_error)

    def test_lockout_period_does_not_query_student_model(self) -> None:
        start = 1_700_000_100.0
        with patch("apps.accounts.views.time.time", return_value=start):
            for _ in range(5):
                self._post(self.wrong_payload)
        fake_filter = MagicMock(return_value=Student.objects.none())
        with patch("apps.accounts.views.time.time", return_value=start + 60), patch(
            "apps.students.models.Student.objects.filter", side_effect=fake_filter
        ):
            self._post(self.correct_payload)
        fake_filter.assert_not_called()

    def test_lockout_error_message_never_exposes_specific_field(self) -> None:
        start = 1_700_000_200.0
        with patch("apps.accounts.views.time.time", return_value=start):
            for _ in range(5):
                self._post(self.empty_payload)
        with patch("apps.accounts.views.time.time", return_value=start + 10):
            wrong_name_response = self._post({"name": "错", "student_number": "ST20260009"})
            wrong_number_response = self._post({"name": "节流测试生", "student_number": "S99999999"})
            empty_response = self._post(self.empty_payload)
        for response in [wrong_name_response, wrong_number_response, empty_response]:
            content = response.content.decode("utf-8")
            self.assertIn(self.lockout_error, content)
            self.assertNotIn("姓名错误", content)
            self.assertNotIn("学号错误", content)
