from django.test import TestCase
from django.urls import reverse

from apps.students.models import DevelopmentStage, PartyBranch, Student, StudentStatus

class StudentSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.branch = PartyBranch.objects.create(code="SESS_T", name="会话测试支部")
        cls.student = Student.objects.create(
            name="周八",
            student_number="SESS001",
            branch=cls.branch,
            development_stage=DevelopmentStage.ACTIVIST,
            status=StudentStatus.ACTIVE,
        )
        cls.login_url = reverse("accounts:student_login")
        cls.profile_url = reverse("students:student_profile")
        cls.logout_url = reverse("accounts:student_logout")

    def test_session_cookie_age_is_thirty_minutes(self) -> None:
        from django.conf import settings
        self.assertEqual(settings.SESSION_COOKIE_AGE, 1800)

    def test_login_writes_student_id(self) -> None:
        self.client.post(self.login_url, {"name": "周八", "student_number": "SESS001"})
        self.assertEqual(self.client.session.get("student_id"), self.student.pk)

    def test_profile_accessible_after_login(self) -> None:
        self.client.post(self.login_url, {"name": "周八", "student_number": "SESS001"})
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)

    def test_profile_inaccessible_after_logout(self) -> None:
        self.client.post(self.login_url, {"name": "周八", "student_number": "SESS001"})
        self.client.post(self.logout_url)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.login_url)

    def test_expired_session_cleaned_on_access(self) -> None:
        session = self.client.session
        session["student_id"] = self.student.pk
        session.save()
        self.student.delete()
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("student_id", self.client.session)

    def test_student_logout_redirects_to_login(self) -> None:
        self.client.post(self.login_url, {"name": "周八", "student_number": "SESS001"})
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.login_url)

    def test_logout_when_not_logged_in_still_redirects(self) -> None:
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.login_url)
