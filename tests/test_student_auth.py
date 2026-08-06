from django.test import TestCase
from django.urls import reverse

from apps.students.models import DevelopmentStage, PartyBranch, Student, StudentStatus

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

    def test_correct_credentials_login(self) -> None:
        response = self.client.post(self.login_url, {"name": "张三", "student_number": "AUTH001"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.profile_url)
        self.assertEqual(self.client.session.get("student_id"), self.active_student.pk)

    def test_wrong_name_unified_error(self) -> None:
        response = self.client.post(self.login_url, {"name": "错误", "student_number": "AUTH001"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("姓名或学号不正确", response.content.decode())
        self.assertNotIn("student_id", self.client.session)

    def test_wrong_number_unified_error(self) -> None:
        response = self.client.post(self.login_url, {"name": "张三", "student_number": "WRONG"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("姓名或学号不正确", response.content.decode())
        self.assertNotIn("student_id", self.client.session)

    def test_empty_input_no_session(self) -> None:
        response = self.client.post(self.login_url, {"name": "", "student_number": ""})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("student_id", self.client.session)

    def test_inactive_student_can_login(self) -> None:
        response = self.client.post(self.login_url, {"name": "李四", "student_number": "AUTH002"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get("student_id"), self.inactive_student.pk)

    def test_get_request_shows_form(self) -> None:
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

class StudentLogoutViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.branch = PartyBranch.objects.create(code="LOGOUT_T", name="退出测试支部")
        cls.student = Student.objects.create(
            name="王五",
            student_number="LOG001",
            branch=cls.branch,
            development_stage=DevelopmentStage.FULL_MEMBER,
            status=StudentStatus.ACTIVE,
        )
        cls.login_url = reverse("accounts:student_login")
        cls.logout_url = reverse("accounts:student_logout")

    def test_get_logout_returns_405(self) -> None:
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 405)

    def test_post_logout_deletes_student_id(self) -> None:
        self.client.post(self.login_url, {"name": "王五", "student_number": "LOG001"})
        self.assertIn("student_id", self.client.session)
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("student_id", self.client.session)

    def test_logout_does_not_affect_admin_auth(self) -> None:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin = User.objects.create_user(username="admin_test", password="pass123")
        self.client.login(username="admin_test", password="pass123")
        self.client.post(self.login_url, {"name": "王五", "student_number": "LOG001"})
        self.client.post(self.logout_url)
        self.assertNotIn("student_id", self.client.session)
        self.assertTrue("_auth_user_id" in self.client.session)
        self.assertEqual(self.client.session.get("_auth_user_id"), str(admin.pk))

class StudentAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.branch = PartyBranch.objects.create(code="ACCESS_T", name="访问测试支部")
        cls.student_a = Student.objects.create(
            name="赵六",
            student_number="ACC001",
            branch=cls.branch,
            development_stage=DevelopmentStage.ACTIVIST,
            status=StudentStatus.ACTIVE,
        )
        cls.student_b = Student.objects.create(
            name="孙七",
            student_number="ACC002",
            branch=cls.branch,
            development_stage=DevelopmentStage.PROBATIONARY,
            status=StudentStatus.ACTIVE,
        )
        cls.login_url = reverse("accounts:student_login")
        cls.profile_url = reverse("students:student_profile")

    def test_anonymous_redirected_to_login(self) -> None:
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.login_url)

    def test_invalid_session_cleaned_and_redirected(self) -> None:
        session = self.client.session
        session["student_id"] = 99999999
        session.save()
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("student_id", self.client.session)

    def test_non_integer_session_cleaned(self) -> None:
        session = self.client.session
        session["student_id"] = "abc"
        session.save()
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("student_id", self.client.session)

    def test_query_param_cannot_override_session(self) -> None:
        self.client.post(self.login_url, {"name": "赵六", "student_number": "ACC001"})
        forged_url = f"{self.profile_url}?student_id={self.student_b.pk}"
        response = self.client.get(forged_url)
        self.assertEqual(response.status_code, 200)

    def test_post_param_cannot_override_session(self) -> None:
        self.client.post(self.login_url, {"name": "赵六", "student_number": "ACC001"})
        response = self.client.post(self.profile_url, {"student_id": self.student_b.pk})
        self.assertEqual(response.status_code, 200)
