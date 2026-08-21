from __future__ import annotations

from datetime import date
from unittest.mock import patch

from django.test import Client
from django.urls import reverse

from apps.imports.models import ImportBatch, ImportStatus
from apps.imports.rollback_service import RollbackBatchNotFound, assess_rollback, get_rollback_candidate
from apps.imports.snapshots import ROLLBACK_FILENAME
from apps.imports.storage import artifact_path
from apps.audit.models import OperationLog
from apps.materials.models import ApplicationRecord, IdeologicalReport, IdeologicalReportSummary
from apps.students.models import PartyBranch, Student
from tests.test_excel_import_preview import ExcelPreviewTestCase


class RollbackAssessmentTests(ExcelPreviewTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.branch = PartyBranch.objects.create(code="MINGLI", name="明理党支部")
        self._login_data_admin()

    def _confirmed_batch(self) -> ImportBatch:
        upload = self._post_upload(self._result())
        self.assertEqual(upload.status_code, 302)
        batch = ImportBatch.objects.latest("pk")
        confirm = self.client.post(reverse("imports:confirm", args=[batch.pk]))
        self.assertEqual(confirm.status_code, 302)
        batch.refresh_from_db()
        return batch

    def _codes(self, batch: ImportBatch) -> set[str]:
        return {conflict.code for conflict in assess_rollback(batch.pk).conflicts}

    def test_latest_success_with_untouched_data_is_eligible(self) -> None:
        batch = self._confirmed_batch()
        assessment = assess_rollback(batch.pk)
        self.assertTrue(assessment.eligible)
        self.assertEqual(assessment.conflicts, ())
        self.assertEqual(assessment.impact.new_students_to_delete, 1)
        self.assertEqual(get_rollback_candidate(), batch)

    def test_missing_batch_raises_domain_not_found(self) -> None:
        with self.assertRaises(RollbackBatchNotFound):
            assess_rollback(999999)

    def test_non_success_states_are_ineligible(self) -> None:
        for status in (ImportStatus.PREVIEWED, ImportStatus.FAILED, ImportStatus.ROLLED_BACK):
            with self.subTest(status=status):
                batch = ImportBatch.objects.create(
                    batch_label=status, original_filename="x.xlsx", status=status
                )
                self.assertIn("BATCH_STATUS_NOT_SUCCESS", self._codes(batch))

    def test_only_latest_success_batch_is_eligible(self) -> None:
        first = self._confirmed_batch()
        second = self._confirmed_batch()
        self.assertIn("BATCH_NOT_LATEST_SUCCESS", self._codes(first))
        self.assertEqual(get_rollback_candidate(), second)

    def test_missing_or_tampered_evidence_is_ineligible(self) -> None:
        batch = self._confirmed_batch()
        artifact_path(batch.pk, ROLLBACK_FILENAME).unlink()
        self.assertIn("ROLLBACK_EVIDENCE_INVALID", self._codes(batch))

    def test_student_post_import_change_is_detected(self) -> None:
        batch = self._confirmed_batch()
        student = Student.objects.get(student_number="20260001")
        student.position = "导入后人工修改"
        student.save(update_fields=["position", "updated_at"])
        self.assertIn("STUDENT_MODIFIED_AFTER_IMPORT", self._codes(batch))

    def test_change_then_restore_same_value_is_detected_by_timestamp(self) -> None:
        batch = self._confirmed_batch()
        student = Student.objects.get(student_number="20260001")
        original = student.position
        student.position = "临时修改"
        student.save()
        student.position = original
        student.save()
        self.assertIn("STUDENT_MODIFIED_AFTER_IMPORT", self._codes(batch))

    def test_application_post_import_change_is_detected(self) -> None:
        batch = self._confirmed_batch()
        application = ApplicationRecord.objects.get()
        application.applied_at = date(2030, 1, 1)
        application.save(update_fields=["applied_at", "updated_at"])
        self.assertIn("APPLICATION_MODIFIED_AFTER_IMPORT", self._codes(batch))

    def test_summary_post_import_change_is_detected(self) -> None:
        batch = self._confirmed_batch()
        summary = IdeologicalReportSummary.objects.get()
        summary.reported_total_count = 99
        summary.save(update_fields=["reported_total_count", "updated_at"])
        self.assertIn("SUMMARY_MODIFIED_AFTER_IMPORT", self._codes(batch))

    def test_report_post_import_change_is_detected(self) -> None:
        batch = self._confirmed_batch()
        report = IdeologicalReport.objects.get()
        report.submitted_at = date(2030, 1, 1)
        report.save(update_fields=["submitted_at"])
        self.assertIn("REPORTS_MODIFIED_AFTER_IMPORT", self._codes(batch))

    def test_missing_current_student_is_detected(self) -> None:
        batch = self._confirmed_batch()
        Student.objects.get(student_number="20260001").delete()
        self.assertIn("CURRENT_STUDENT_MISSING", self._codes(batch))

    def test_existing_student_impact_uses_pre_import_snapshot(self) -> None:
        student = Student.objects.create(
            name="旧姓名",
            student_number="20260001",
            branch=self.branch,
            development_stage="FULL_MEMBER",
        )
        ApplicationRecord.objects.create(student=student, applied_at=date(2020, 1, 1))
        IdeologicalReportSummary.objects.create(
            student=student, reported_total_count=1, calculated_date_count=1
        )
        IdeologicalReport.objects.create(
            student=student,
            sequence_number=2,
            submitted_at=date(2020, 2, 2),
            source_column_name="第二次思想汇报",
        )
        batch = self._confirmed_batch()
        impact = assess_rollback(batch.pk).impact
        self.assertEqual(impact.existing_students_to_restore, 1)
        self.assertEqual(impact.new_students_to_delete, 0)
        self.assertEqual(impact.applications_to_restore, 1)
        self.assertEqual(impact.summaries_to_restore, 1)
        self.assertEqual(impact.reports_to_replace, 1)

    def test_rollback_page_permissions_method_and_csrf(self) -> None:
        batch = self._confirmed_batch()
        url = reverse("imports:rollback", args=[batch.pk])
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(url).status_code, 403)
        self._login_data_admin()
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get(url), "回滚影响预览")
        self.assertEqual(self.client.put(url).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.data_admin)
        self.assertEqual(
            csrf_client.post(url, {"confirm_batch_id": str(batch.pk)}).status_code, 403
        )

    def test_post_requires_exact_second_confirmation(self) -> None:
        batch = self._confirmed_batch()
        url = reverse("imports:rollback", args=[batch.pk])
        self.assertEqual(self.client.post(url).status_code, 400)
        self.assertEqual(self.client.post(url, {"confirm_batch_id": "999"}).status_code, 400)
        batch.refresh_from_db()
        self.assertEqual(batch.status, ImportStatus.SUCCESS)

    def test_rollback_deletes_student_created_by_import_and_records_audit(self) -> None:
        batch = self._confirmed_batch()
        response = self.client.post(
            reverse("imports:rollback", args=[batch.pk]),
            {"confirm_batch_id": str(batch.pk)},
        )
        batch.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(batch.status, ImportStatus.ROLLED_BACK)
        self.assertEqual(batch.rolled_back_by, self.data_admin)
        self.assertIsNotNone(batch.rolled_back_at)
        self.assertFalse(Student.objects.filter(student_number="20260001").exists())
        self.assertEqual(
            OperationLog.objects.filter(action="rollback_import", target_id=str(batch.pk)).count(),
            1,
        )

    def test_rollback_restores_existing_student_and_all_materials(self) -> None:
        old_batch = ImportBatch.objects.create(
            batch_label="old", original_filename="old.xlsx", status=ImportStatus.SUCCESS
        )
        student = Student.objects.create(
            name="旧姓名",
            student_number="20260001",
            branch=self.branch,
            development_stage="FULL_MEMBER",
            position="旧职务",
            source_import_batch=old_batch,
        )
        application = ApplicationRecord.objects.create(
            student=student, applied_at=date(2020, 1, 1), source_import_batch=old_batch
        )
        summary = IdeologicalReportSummary.objects.create(
            student=student,
            reported_total_count=7,
            calculated_date_count=1,
            source_import_batch=old_batch,
        )
        old_report = IdeologicalReport.objects.create(
            student=student,
            sequence_number=2,
            submitted_at=date(2020, 2, 2),
            source_column_name="第二次思想汇报",
            import_batch=old_batch,
        )
        batch = self._confirmed_batch()
        response = self.client.post(
            reverse("imports:rollback", args=[batch.pk]),
            {"confirm_batch_id": str(batch.pk)},
        )
        self.assertEqual(response.status_code, 302)
        student.refresh_from_db()
        application.refresh_from_db()
        summary.refresh_from_db()
        self.assertEqual(student.name, "旧姓名")
        self.assertEqual(student.development_stage, "FULL_MEMBER")
        self.assertEqual(student.position, "旧职务")
        self.assertEqual(student.source_import_batch, old_batch)
        self.assertEqual(application.applied_at, date(2020, 1, 1))
        self.assertEqual(application.source_import_batch, old_batch)
        self.assertEqual(summary.reported_total_count, 7)
        self.assertEqual(summary.source_import_batch, old_batch)
        reports = list(student.ideological_reports.filter(is_active=True))
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].pk, old_report.pk)
        self.assertEqual(reports[0].sequence_number, 2)
        self.assertEqual(reports[0].import_batch, old_batch)

    def test_conflict_post_returns_409_and_changes_nothing(self) -> None:
        batch = self._confirmed_batch()
        student = Student.objects.get(student_number="20260001")
        student.position = "后续修改"
        student.save()
        response = self.client.post(
            reverse("imports:rollback", args=[batch.pk]),
            {"confirm_batch_id": str(batch.pk)},
        )
        self.assertEqual(response.status_code, 409)
        batch.refresh_from_db()
        student.refresh_from_db()
        self.assertEqual(batch.status, ImportStatus.SUCCESS)
        self.assertEqual(student.position, "后续修改")
        self.assertFalse(OperationLog.objects.filter(action="rollback_import").exists())

    def test_repeated_rollback_returns_409(self) -> None:
        batch = self._confirmed_batch()
        url = reverse("imports:rollback", args=[batch.pk])
        payload = {"confirm_batch_id": str(batch.pk)}
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        self.assertEqual(self.client.post(url, payload).status_code, 409)

    def test_audit_failure_rolls_back_entire_restore_transaction(self) -> None:
        batch = self._confirmed_batch()
        student = Student.objects.get(student_number="20260001")
        with patch(
            "apps.imports.rollback_service.record_operation_log",
            side_effect=RuntimeError("audit failure"),
        ):
            response = self.client.post(
                reverse("imports:rollback", args=[batch.pk]),
                {"confirm_batch_id": str(batch.pk)},
            )
        self.assertEqual(response.status_code, 500)
        batch.refresh_from_db()
        self.assertEqual(batch.status, ImportStatus.SUCCESS)
        self.assertTrue(Student.objects.filter(pk=student.pk).exists())
        self.assertFalse(OperationLog.objects.filter(action="rollback_import").exists())
