from django.test import TestCase
from django.urls import reverse

from apps.accounts.decorators import admin_url_forbid_student, student_login_required
from apps.students.models import DevelopmentStage, PartyBranch, Student, StudentStatus


class StudentLoginRequiredReuseTests(TestCase):
    def test_decorators_importable_from_decorators_module(self) -> None:
        self.assertTrue(callable(student_login_required))
        self.assertTrue(callable(admin_url_forbid_student))


class StudentLoginRequiredBehaviorTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.branch = PartyBranch.objects.create(code="DEC_TEST", name="装饰器测试支部")
        cls.student_a = Student.objects.create(
            name="学生A",
            student_number="SA20260001",
            branch=cls.branch,
            development_stage=DevelopmentStage.ACTIVIST,
            status=StudentStatus.ACTIVE,
        )
        cls.student_b = Student.objects.create(
            name="学生B",
            student_number="SB20260002",
            branch=cls.branch,
            development_stage=DevelopmentStage.PROBATIONARY,
            status=StudentStatus.ACTIVE,
        )
        cls.login_url = reverse("accounts:student_login")
        cls.profile_url = reverse("students:student_profile")
        cls.admin_list_url = reverse("students:admin_student_list")
        cls.admin_detail_url = reverse("students:admin_student_detail", kwargs={"pk": cls.student_a.pk})

    def _login_as(self, student: Student) -> None:
        self.client.post(
            self.login_url,
            {"name": student.name, "student_number": student.student_number},
        )

    def test_anonymous_redirected_to_login(self) -> None:
        response = self.client.get(self.profile_url)
        self.assertRedirects(response, self.login_url, fetch_redirect_response=False)

    def test_logged_in_student_accessible_profile(self) -> None:
        self._login_as(self.student_a)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_student_id"], self.student_a.pk)
        self.assertEqual(response.context["student"].pk, self.student_a.pk)

    def test_url_fake_student_id_query_param_ignored(self) -> None:
        self._login_as(self.student_a)
        forged_url = f"{self.profile_url}?student_id={self.student_b.pk}"
        response = self.client.get(forged_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_student_id"], self.student_a.pk)
        self.assertEqual(response.context["student"].pk, self.student_a.pk)
        self.assertNotEqual(response.context["current_student_id"], self.student_b.pk)


class AdminUrlForbidStudentTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.branch = PartyBranch.objects.create(code="ADM_GUARD", name="管理员保护支部")
        cls.student = Student.objects.create(
            name="学生C",
            student_number="SC20260003",
            branch=cls.branch,
            development_stage=DevelopmentStage.FULL_MEMBER,
            status=StudentStatus.ACTIVE,
        )
        cls.login_url = reverse("accounts:student_login")
        cls.admin_list_url = reverse("students:admin_student_list")
        cls.admin_detail_url = reverse("students:admin_student_detail", kwargs={"pk": cls.student.pk})

    def _login_student(self) -> None:
        self.client.post(
            self.login_url,
            {"name": "学生C", "student_number": "SC20260003"},
        )

    def test_student_forbidden_on_admin_list(self) -> None:
        self._login_student()
        response = self.client.get(self.admin_list_url)
        self.assertEqual(response.status_code, 403)

    def test_student_forbidden_on_admin_detail(self) -> None:
        self._login_student()
        response = self.client.get(self.admin_detail_url)
        self.assertEqual(response.status_code, 403)

    def test_anonymous_admin_still_accessible_templateview_behavior(self) -> None:
        list_response = self.client.get(self.admin_list_url)
        detail_response = self.client.get(self.admin_detail_url)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
