from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import include, path, reverse

from apps.accounts.student_access import student_required
from apps.students.models import DevelopmentStage, PartyBranch, Student, StudentStatus


@student_required
def protected_student_probe(request):
    """测试专用消费者：返回装饰器验证后的学生主键。"""
    return HttpResponse(str(request.current_student.pk))


urlpatterns = [
    path("", include("config.urls")),
    path("__tests__/student-probe/", protected_student_probe, name="student_probe"),
]


class StudentLoginViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.branch = PartyBranch.objects.create(code="AUTH_TEST", name="认证测试支部")
        cls.active_student = Student.objects.create(
            name="张三",
            student_number="AUTH001",
            branch=cls.branch,
            development_stage=DevelopmentStage.ACTIVIST,
            status=StudentStatus.ACTIVE,
        )
        cls.inactive_student = Student.objects.create(
            name="李四",
            student_number="AUTH002",
            branch=cls.branch,
            development_stage=DevelopmentStage.PROBATIONARY,
            status=StudentStatus.INACTIVE,
        )
        cls.login_url = reverse("accounts:student_login")
        cls.profile_url = reverse("students:student_profile")

    def test_correct_credentials_write_integer_student_id(self) -> None:
        response = self.client.post(
            self.login_url,
            {"name": "张三", "student_number": "AUTH001"},
        )
        self.assertRedirects(response, self.profile_url, fetch_redirect_response=False)
        student_id = self.client.session.get("student_id")
        self.assertIs(type(student_id), int)
        self.assertEqual(student_id, self.active_student.pk)

    def test_credentials_are_trimmed(self) -> None:
        response = self.client.post(
            self.login_url,
            {"name": "  张三  ", "student_number": "  AUTH001  "},
        )
        self.assertRedirects(response, self.profile_url, fetch_redirect_response=False)
        self.assertEqual(self.client.session["student_id"], self.active_student.pk)

    def test_wrong_name_and_wrong_number_use_same_error(self) -> None:
        attempts = (
            {"name": "错误", "student_number": "AUTH001"},
            {"name": "张三", "student_number": "WRONG"},
            {"name": "", "student_number": ""},
        )
        for credentials in attempts:
            with self.subTest(credentials=credentials):
                response = self.client.post(self.login_url, credentials)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "姓名或学号不正确")
                self.assertNotIn("student_id", self.client.session)

    def test_inactive_student_can_login(self) -> None:
        response = self.client.post(
            self.login_url,
            {"name": "李四", "student_number": "AUTH002"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["student_id"], self.inactive_student.pk)

    def test_login_cycles_session_key_and_clears_admin_auth(self) -> None:
        admin = get_user_model().objects.create_user(
            username="admin_auth_test",
            password="pass123",
        )
        self.client.force_login(admin)
        session_before = self.client.session
        old_key = session_before.session_key

        self.client.post(
            self.login_url,
            {"name": "张三", "student_number": "AUTH001"},
        )

        session_after = self.client.session
        self.assertNotEqual(session_after.session_key, old_key)
        self.assertEqual(session_after["student_id"], self.active_student.pk)
        self.assertNotIn("_auth_user_id", session_after)

        upload_response = self.client.get(reverse("imports:upload"))
        self.assertEqual(upload_response.status_code, 302)
        self.assertIn(reverse("accounts:admin_login"), upload_response.url)

    def test_student_navigation_does_not_show_admin_actions(self) -> None:
        self.client.post(
            self.login_url,
            {"name": "张三", "student_number": "AUTH001"},
        )

        response = self.client.get(self.profile_url)

        self.assertContains(response, "学生个人信息")
        self.assertContains(response, "退出学生登录")
        self.assertNotContains(response, "Excel上传")
        self.assertNotContains(response, "退出管理员登录")


@override_settings(ROOT_URLCONF=__name__)
class StudentAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.branch = PartyBranch.objects.create(code="ACCESS_T", name="访问测试支部")
        cls.student_a = Student.objects.create(
            name="赵六",
            student_number="ACC001",
            branch=cls.branch,
            development_stage=DevelopmentStage.ACTIVIST,
        )
        cls.student_b = Student.objects.create(
            name="孙七",
            student_number="ACC002",
            branch=cls.branch,
            development_stage=DevelopmentStage.PROBATIONARY,
        )
        cls.probe_url = "/__tests__/student-probe/"

    def set_student_session(self, value) -> None:
        session = self.client.session
        session["student_id"] = value
        session.save()

    def test_anonymous_is_redirected_to_student_login(self) -> None:
        response = self.client.get(self.probe_url)
        self.assertRedirects(
            response,
            reverse("accounts:student_login"),
            fetch_redirect_response=False,
        )

    def test_valid_session_exposes_verified_student(self) -> None:
        self.set_student_session(self.student_a.pk)
        response = self.client.get(self.probe_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), str(self.student_a.pk))

    def test_invalid_session_values_are_cleaned(self) -> None:
        invalid_values = ("1", "abc", True, 0, -1, 1.5)
        for value in invalid_values:
            with self.subTest(value=value):
                self.client.cookies.clear()
                self.set_student_session(value)
                response = self.client.get(self.probe_url)
                self.assertEqual(response.status_code, 302)
                self.assertNotIn("student_id", self.client.session)

    def test_missing_student_is_cleaned(self) -> None:
        self.set_student_session(99999999)
        response = self.client.get(self.probe_url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("student_id", self.client.session)

    def test_get_and_post_parameters_cannot_override_session_identity(self) -> None:
        self.set_student_session(self.student_a.pk)
        get_response = self.client.get(
            self.probe_url,
            {"student_id": self.student_b.pk},
        )
        post_response = self.client.post(
            self.probe_url,
            {"student_id": self.student_b.pk},
        )
        self.assertEqual(get_response.content.decode(), str(self.student_a.pk))
        self.assertEqual(post_response.content.decode(), str(self.student_a.pk))

    def test_database_system_error_is_not_swallowed(self) -> None:
        self.set_student_session(self.student_a.pk)
        with patch(
            "apps.accounts.student_access.Student.objects.select_related",
            side_effect=RuntimeError("database unavailable"),
        ):
            with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                self.client.get(self.probe_url)
