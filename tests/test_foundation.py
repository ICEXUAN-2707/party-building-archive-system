from datetime import date

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import resolve, reverse

from apps.accounts.models import AdminRole
from apps.imports.models import ImportStatus
from apps.materials.models import ApplicationRecord, IdeologicalReport, IdeologicalReportSummary
from apps.students.management.commands.initialize_branches import BRANCHES
from apps.students.models import DevelopmentStage, PartyBranch, Student


class FoundationPageTests(TestCase):
    def test_home_page_returns_success(self) -> None:
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "学院学生材料信息查询系统")

    def test_placeholder_urls_resolve(self) -> None:
        url_names = [
            "accounts:student_login",
            "accounts:admin_login",
            "students:student_profile",
            "students:admin_student_list",
            "imports:upload",
            "imports:history",
        ]
        for name in url_names:
            with self.subTest(name=name):
                self.assertIsNotNone(resolve(reverse(name)))
        self.assertIsNotNone(resolve(reverse("students:admin_student_detail", kwargs={"pk": 1})))
        self.assertIsNotNone(resolve(reverse("imports:preview", kwargs={"batch_id": 1})))
        self.assertIsNotNone(resolve(reverse("imports:batch_detail", kwargs={"batch_id": 1})))
        self.assertIsNotNone(resolve(reverse("imports:download_file", kwargs={"batch_id": 1})))


class BranchCommandTests(TestCase):
    def test_initialize_branches_creates_nine_branches(self) -> None:
        call_command("initialize_branches", verbosity=0)
        self.assertEqual(PartyBranch.objects.count(), 9)
        self.assertEqual(set(PartyBranch.objects.values_list("code", flat=True)), {code for code, _ in BRANCHES})

    def test_initialize_branches_is_idempotent(self) -> None:
        call_command("initialize_branches", verbosity=0)
        call_command("initialize_branches", verbosity=0)
        self.assertEqual(PartyBranch.objects.count(), 9)


class CoreModelTests(TestCase):
    def setUp(self) -> None:
        self.branch = PartyBranch.objects.create(code="TEST", name="测试党支部")
        self.student = Student.objects.create(
            name="测试学生",
            student_number="T20269999",
            branch=self.branch,
            development_stage=DevelopmentStage.ACTIVIST,
        )

    def test_core_models_can_be_created(self) -> None:
        application = ApplicationRecord.objects.create(student=self.student, applied_at=date(2025, 1, 1))
        summary = IdeologicalReportSummary.objects.create(
            student=self.student,
            reported_total_count=2,
            calculated_date_count=2,
        )
        report = IdeologicalReport.objects.create(
            student=self.student,
            sequence_number=1,
            submitted_at=date(2025, 2, 1),
            source_column_name="第1次思想汇报",
        )
        self.assertEqual(application.student, self.student)
        self.assertEqual(summary.student, self.student)
        self.assertEqual(report.student, self.student)

    def test_frozen_enums_are_valid(self) -> None:
        self.assertEqual(
            {choice.value for choice in DevelopmentStage},
            {"ACTIVIST", "PROBATIONARY", "FULL_MEMBER"},
        )
        self.assertEqual({choice.value for choice in AdminRole}, {"viewer_admin", "data_admin"})
        self.assertEqual({choice.value for choice in ImportStatus}, {"previewed", "success", "failed", "rolled_back"})

    def test_student_branch_relationship(self) -> None:
        self.assertEqual(self.branch.students.get(), self.student)

    def test_application_record_is_one_to_one(self) -> None:
        ApplicationRecord.objects.create(student=self.student, applied_at=date(2025, 1, 1))
        self.assertEqual(self.student.application_record.applied_at, date(2025, 1, 1))

    def test_report_summary_is_one_to_one(self) -> None:
        IdeologicalReportSummary.objects.create(student=self.student, calculated_date_count=0)
        self.assertEqual(self.student.report_summary.calculated_date_count, 0)

    def test_student_can_have_multiple_reports(self) -> None:
        IdeologicalReport.objects.create(
            student=self.student,
            sequence_number=1,
            submitted_at=date(2025, 2, 1),
            source_column_name="第1次思想汇报",
        )
        IdeologicalReport.objects.create(
            student=self.student,
            sequence_number=2,
            submitted_at=date(2025, 3, 1),
            source_column_name="第2次思想汇报",
        )
        self.assertEqual(self.student.ideological_reports.count(), 2)

    def test_report_sequence_number_must_be_positive(self) -> None:
        report = IdeologicalReport(
            student=self.student,
            sequence_number=0,
            submitted_at=date(2025, 2, 1),
            source_column_name="第0次思想汇报",
        )
        with self.assertRaises(ValidationError):
            report.full_clean()


class DemoDataCommandTests(TestCase):
    def test_seed_demo_data_command_is_idempotent(self) -> None:
        call_command("seed_demo_data", verbosity=0)
        call_command("seed_demo_data", verbosity=0)
        self.assertEqual(Student.objects.filter(student_number__startswith="T2026").count(), 4)
        self.assertGreaterEqual(IdeologicalReport.objects.count(), 8)
