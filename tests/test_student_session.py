from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from apps.students.models import DevelopmentStage, PartyBranch, Student, StudentStatus


class StudentSessionConfigTests(TestCase):
    def test_session_cookie_age_is_thirty_minutes(self) -> None:
        self.assertEqual(settings.SESSION_COOKIE_AGE, 1800)


class StudentLogoutViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.branch = PartyBranch.objects.create(code="LOGOUT_TEST", name="退出测试支部")
        cls.student = Student.objects.create(
            name="王五",
            student_number="S20260003",
            branch=cls.branch,
            development_stage=DevelopmentStage.FULL_MEMBER,
            status=StudentStatus.ACTIVE,
        )
        cls.login_url = reverse("accounts:student_login")
        cls.logout_url = reverse("accounts:student_logout")
        cls.profile_url = reverse("students:student_profile")

    def _login(self) -> None:
        self.client.post(
            self.login_url,
            {"name": "王五", "student_number": "S20260003"},
        )

    def test_logout_clears_student_id_from_session(self) -> None:
        self._login()
        self.assertEqual(self.client.session.get("student_id"), self.student.id)
        self.client.get(self.logout_url)
        self.assertIsNone(self.client.session.get("student_id"))

    def test_logout_redirects_to_login_page(self) -> None:
        self._login()
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.login_url, fetch_redirect_response=False)

    def test_logout_when_not_logged_in_still_redirects_to_login(self) -> None:
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.login_url, fetch_redirect_response=False)

    def test_cannot_access_profile_after_logout(self) -> None:
        self._login()
        self.client.get(self.logout_url)
        profile_response = self.client.get(self.profile_url)
        self.assertRedirects(profile_response, self.login_url, fetch_redirect_response=False)


class StudentLoginRequiredTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.branch = PartyBranch.objects.create(code="GUARD_TEST", name="保护测试支部")
        cls.student = Student.objects.create(
            name="赵六",
            student_number="S20260004",
            branch=cls.branch,
            development_stage=DevelopmentStage.ACTIVIST,
            status=StudentStatus.ACTIVE,
        )
        cls.login_url = reverse("accounts:student_login")
        cls.profile_url = reverse("students:student_profile")

    def _login(self) -> None:
        self.client.post(
            self.login_url,
            {"name": "赵六", "student_number": "S20260004"},
        )

    def test_profile_requires_login_redirects_anonymous(self) -> None:
        response = self.client.get(self.profile_url)
        self.assertRedirects(response, self.login_url, fetch_redirect_response=False)

    def test_profile_accessible_after_login(self) -> None:
        self._login()
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/student_profile.html")

    def test_profile_inaccessible_after_session_flush(self) -> None:
        self._login()
        self.assertEqual(self.client.session.get("student_id"), self.student.id)
        session = self.client.session
        session.flush()
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        profile_response = self.client.get(self.profile_url)
        self.assertRedirects(profile_response, self.login_url, fetch_redirect_response=False)

    def test_profile_inaccessible_without_valid_student_in_session(self) -> None:
        session = self.client.session
        session["student_id"] = 99999999
        session.save()
        profile_response = self.client.get(self.profile_url)
        self.assertEqual(profile_response.status_code, 200)
