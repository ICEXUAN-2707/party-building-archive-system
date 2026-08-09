from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class StudentLogoutViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.logout_url = reverse("accounts:student_logout")
        cls.login_url = reverse("accounts:student_login")

    def test_get_logout_returns_405(self) -> None:
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 405)

    def test_post_logout_only_removes_student_id(self) -> None:
        admin = get_user_model().objects.create_user(
            username="admin_logout_test",
            password="pass123",
        )
        self.client.force_login(admin)
        session = self.client.session
        session["student_id"] = 123
        session["unrelated_session_value"] = "keep"
        session.save()

        response = self.client.post(self.logout_url)

        self.assertRedirects(response, self.login_url, fetch_redirect_response=False)
        self.assertNotIn("student_id", self.client.session)
        self.assertEqual(self.client.session["_auth_user_id"], str(admin.pk))
        self.assertEqual(self.client.session["unrelated_session_value"], "keep")

    def test_logout_without_student_session_is_idempotent(self) -> None:
        response = self.client.post(self.logout_url)
        self.assertRedirects(response, self.login_url, fetch_redirect_response=False)

    def test_logout_requires_csrf_token(self) -> None:
        csrf_client = Client(enforce_csrf_checks=True)
        session = csrf_client.session
        session["student_id"] = 123
        session.save()

        rejected = csrf_client.post(self.logout_url)
        self.assertEqual(rejected.status_code, 403)
        self.assertIn("student_id", csrf_client.session)

        login_page = csrf_client.get(self.login_url)
        csrf_token = login_page.cookies["csrftoken"].value
        accepted = csrf_client.post(
            self.logout_url,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(accepted.status_code, 302)
        self.assertNotIn("student_id", csrf_client.session)
