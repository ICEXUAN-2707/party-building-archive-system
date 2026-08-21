from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date
from unittest.mock import patch

from django.test import Client
from django.urls import reverse

from apps.imports.datatypes import ParseResult, SheetResult
from apps.imports.models import ImportBatch, ImportStatus
from apps.imports.import_service import (
    FAILURE_AUDIT,
    FAILURE_BACKUP,
    PRE_IMPORT_DATABASE_FILENAME,
    ROLLBACK_FILENAME,
    ROLLBACK_HASH_FILENAME,
    _confirmation_lock,
)
from apps.imports.snapshots import PREVIEW_FILENAME, PREVIEW_HASH_FILENAME
from apps.imports.snapshots import load_rollback_snapshot
from apps.imports.storage import artifact_path
from apps.audit.models import OperationLog
from apps.materials.models import ApplicationRecord, IdeologicalReport, IdeologicalReportSummary
from apps.students.models import PartyBranch, Student, StudentStatus
from tests.test_excel_import_preview import ExcelPreviewTestCase


class ConfirmImportGuardTests(ExcelPreviewTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._login_data_admin()

    def _create_batch(self, result: ParseResult | None = None) -> ImportBatch:
        response = self._post_upload(result)
        self.assertEqual(response.status_code, 302)
        return ImportBatch.objects.latest("pk")

    def _confirm_url(self, batch: ImportBatch) -> str:
        return reverse("imports:confirm", args=[batch.pk])

    def _business_counts(self) -> tuple[int, int, int, int]:
        return (
            Student.objects.count(),
            ApplicationRecord.objects.count(),
            IdeologicalReportSummary.objects.count(),
            IdeologicalReport.objects.count(),
        )

    def _rewrite_preview(self, batch: ImportBatch, mutate) -> None:
        preview_path = artifact_path(batch.pk, PREVIEW_FILENAME)
        snapshot = json.loads(preview_path.read_text(encoding="utf-8"))
        mutate(snapshot)
        payload = json.dumps(
            snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        preview_path.write_bytes(payload)
        artifact_path(batch.pk, PREVIEW_HASH_FILENAME).write_text(
            hashlib.sha256(payload).hexdigest(), encoding="ascii"
        )

    def test_anonymous_is_redirected_and_viewer_is_forbidden(self) -> None:
        batch = self._create_batch()
        self.client.logout()
        anonymous = self.client.post(self._confirm_url(batch))
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn(reverse("accounts:admin_login"), anonymous.url)

        self.client.force_login(self.viewer)
        self.assertEqual(self.client.post(self._confirm_url(batch)).status_code, 403)

    def test_inactive_data_admin_is_redirected_by_django_authentication(self) -> None:
        batch = self._create_batch()
        self.data_admin.is_active = False
        self.data_admin.save(update_fields=["is_active"])
        self.client.force_login(self.data_admin)
        response = self.client.post(self._confirm_url(batch))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:admin_login"), response.url)

    def test_unknown_active_role_is_forbidden(self) -> None:
        batch = self._create_batch()
        self.data_admin.role = "unknown_role"
        self.data_admin.save(update_fields=["role"])
        self.client.force_login(self.data_admin)
        self.assertEqual(self.client.post(self._confirm_url(batch)).status_code, 403)

    def test_confirm_only_accepts_post_and_enforces_csrf(self) -> None:
        batch = self._create_batch()
        self.assertEqual(self.client.get(self._confirm_url(batch)).status_code, 405)

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.data_admin)
        self.assertEqual(csrf_client.post(self._confirm_url(batch)).status_code, 403)

    def test_missing_batch_returns_404(self) -> None:
        self.assertEqual(
            self.client.post(reverse("imports:confirm", args=[999999])).status_code,
            404,
        )

    def test_terminal_and_success_states_return_409_before_evidence_read(self) -> None:
        for status in (ImportStatus.SUCCESS, ImportStatus.FAILED, ImportStatus.ROLLED_BACK):
            with self.subTest(status=status):
                batch = ImportBatch.objects.create(
                    batch_label=f"state-{status}",
                    original_filename="missing.xlsx",
                    status=status,
                )
                response = self.client.post(self._confirm_url(batch))
                self.assertEqual(response.status_code, 409)
                self.assertContains(response, "状态不允许确认", status_code=409)

    def test_repeated_request_for_completed_batch_is_idempotent(self) -> None:
        batch = self._create_batch()
        batch.status = ImportStatus.SUCCESS
        batch.save(update_fields=["status"])
        before = self._business_counts()

        first = self.client.post(self._confirm_url(batch))
        second = self.client.post(self._confirm_url(batch))

        self.assertEqual((first.status_code, second.status_code), (409, 409))
        self.assertEqual(self._business_counts(), before)

    def test_original_file_hash_change_returns_409_and_zero_writes(self) -> None:
        batch = self._create_batch()
        before = self._business_counts()
        with batch.stored_file.storage.open(batch.stored_file.name, "ab") as stored:
            stored.write(b"tampered")

        response = self.client.post(self._confirm_url(batch))

        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "完整性校验失败", status_code=409)
        self.assertEqual(self._business_counts(), before)

    def test_missing_or_tampered_preview_returns_409(self) -> None:
        batch = self._create_batch()
        preview_path = artifact_path(batch.pk, PREVIEW_FILENAME)
        preview_path.write_bytes(preview_path.read_bytes() + b" ")
        self.assertEqual(self.client.post(self._confirm_url(batch)).status_code, 409)

        batch = self._create_batch()
        artifact_path(batch.pk, PREVIEW_FILENAME).unlink()
        self.assertEqual(self.client.post(self._confirm_url(batch)).status_code, 409)

    def test_empty_candidates_return_409(self) -> None:
        empty = ParseResult(
            total_sheets=1,
            success_sheets=1,
            sheet_results=[SheetResult("明理党支部", "MINGLI", "明理党支部", "success")],
        )
        batch = self._create_batch(empty)
        response = self.client.post(self._confirm_url(batch))
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "没有有效候选数据", status_code=409)

    def test_duplicate_student_numbers_return_409(self) -> None:
        result = self._result()
        result.valid_rows.append(self._result().valid_rows[0])
        result.success_rows = 2
        result.total_rows = 2
        result.sheet_results[0].valid_row_count = 2
        result.sheet_results[0].total_rows = 2
        batch = self._create_batch(result)
        response = self.client.post(self._confirm_url(batch))
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "重复学号冲突", status_code=409)

    def test_valid_preview_is_imported_and_client_rows_are_ignored(self) -> None:
        PartyBranch.objects.get_or_create(code="MINGLI", defaults={"name": "明理党支部"})
        batch = self._create_batch()
        response = self.client.post(
            self._confirm_url(batch),
            {"valid_rows": "client supplied data must be ignored"},
        )
        batch.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("imports:batch_detail", args=[batch.pk]))
        self.assertEqual(batch.status, ImportStatus.SUCCESS)
        self.assertEqual(Student.objects.get().student_number, "20260001")


class ConfirmImportTransactionTests(ConfirmImportGuardTests):
    def setUp(self) -> None:
        super().setUp()
        self.branch = PartyBranch.objects.create(code="MINGLI", name="明理党支部")

    def test_success_creates_evidence_backup_statistics_and_audit(self) -> None:
        batch = self._create_batch()
        response = self.client.post(self._confirm_url(batch))
        batch.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(batch.status, ImportStatus.SUCCESS)
        self.assertIsNotNone(batch.imported_at)
        self.assertEqual(batch.imported_by, self.data_admin)
        self.assertEqual(batch.created_students, 1)
        self.assertEqual(batch.updated_students, 0)
        self.assertEqual(batch.created_reports, 1)
        self.assertEqual(batch.updated_applications, 1)

        rollback_path = artifact_path(batch.pk, ROLLBACK_FILENAME)
        rollback_hash = artifact_path(batch.pk, ROLLBACK_HASH_FILENAME).read_text(
            encoding="ascii"
        )
        self.assertEqual(hashlib.sha256(rollback_path.read_bytes()).hexdigest(), rollback_hash)
        rollback = json.loads(rollback_path.read_text(encoding="utf-8"))
        self.assertEqual(rollback["schema_version"], 1)
        self.assertEqual(rollback["import_batch_id"], batch.pk)
        self.assertEqual(rollback["record_count"], 1)
        self.assertFalse(rollback["students"][0]["student_existed_before"])

        backup_path = artifact_path(batch.pk, PRE_IMPORT_DATABASE_FILENAME)
        backup = sqlite3.connect(backup_path)
        try:
            self.assertEqual(backup.execute("PRAGMA integrity_check").fetchone(), ("ok",))
            self.assertEqual(backup.execute("SELECT COUNT(*) FROM students_student").fetchone(), (0,))
            self.assertEqual(
                backup.execute(
                    "SELECT status FROM imports_importbatch WHERE id = ?", (batch.pk,)
                ).fetchone(),
                (ImportStatus.PREVIEWED,),
            )
        finally:
            backup.close()
        self.assertEqual(
            OperationLog.objects.filter(action="confirm_import", target_id=str(batch.pk)).count(),
            1,
        )

    def test_existing_student_uses_frozen_empty_value_and_replacement_rules(self) -> None:
        old_batch = ImportBatch.objects.create(
            batch_label="old", original_filename="old.xlsx", status=ImportStatus.SUCCESS
        )
        student = Student.objects.create(
            name="旧姓名",
            student_number="20260001",
            branch=self.branch,
            development_stage="FULL_MEMBER",
            position="旧职务",
            status=StudentStatus.INACTIVE,
            source_import_batch=old_batch,
        )
        application = ApplicationRecord.objects.create(
            student=student,
            applied_at=date(2020, 1, 2),
            source_import_batch=old_batch,
        )
        summary = IdeologicalReportSummary.objects.create(
            student=student,
            reported_total_count=9,
            calculated_date_count=1,
            source_import_batch=old_batch,
        )
        IdeologicalReport.objects.create(
            student=student,
            sequence_number=3,
            submitted_at=date(2020, 3, 4),
            source_column_name="第三次思想汇报",
            import_batch=old_batch,
        )
        result = self._result(include_warning=False)
        row = result.valid_rows[0]
        row.position = ""
        row.applied_at = None
        row.reported_total_count = None
        row.name = "新姓名"
        batch = self._create_batch(result)

        response = self.client.post(self._confirm_url(batch))
        student.refresh_from_db()
        application.refresh_from_db()
        summary.refresh_from_db()
        batch.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(student.name, "新姓名")
        self.assertEqual(student.position, "旧职务")
        self.assertEqual(student.status, StudentStatus.INACTIVE)
        self.assertEqual(student.source_import_batch, batch)
        self.assertEqual(application.applied_at, date(2020, 1, 2))
        self.assertEqual(application.source_import_batch, old_batch)
        self.assertEqual(summary.reported_total_count, 9)
        self.assertEqual(summary.calculated_date_count, 1)
        self.assertEqual(summary.source_import_batch, batch)
        reports = list(student.ideological_reports.filter(is_active=True))
        self.assertEqual([(item.sequence_number, item.import_batch_id) for item in reports], [(1, batch.pk)])
        self.assertEqual(batch.created_students, 0)
        self.assertEqual(batch.updated_students, 1)
        self.assertEqual(batch.updated_applications, 0)

        rollback = json.loads(
            artifact_path(batch.pk, ROLLBACK_FILENAME).read_text(encoding="utf-8")
        )["students"][0]
        self.assertTrue(rollback["student_existed_before"])
        self.assertEqual(rollback["student"]["name"], "旧姓名")
        self.assertEqual(rollback["application_record"]["applied_at"], "2020-01-02")
        self.assertEqual(rollback["report_summary"]["reported_total_count"], 9)
        self.assertEqual(rollback["active_reports"][0]["sequence_number"], 3)

    def test_repeated_confirm_after_real_success_is_409_and_has_no_side_effect(self) -> None:
        batch = self._create_batch()
        self.assertEqual(self.client.post(self._confirm_url(batch)).status_code, 302)
        counts = self._business_counts()
        audit_count = OperationLog.objects.filter(action="confirm_import").count()

        response = self.client.post(self._confirm_url(batch))

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self._business_counts(), counts)
        self.assertEqual(OperationLog.objects.filter(action="confirm_import").count(), audit_count)

    def test_audit_failure_rolls_back_business_writes_and_marks_batch_failed(self) -> None:
        batch = self._create_batch()
        before = self._business_counts()
        with patch("apps.imports.import_service.record_operation_log", side_effect=RuntimeError("audit")):
            response = self.client.post(self._confirm_url(batch))
        batch.refresh_from_db()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(batch.status, ImportStatus.FAILED)
        self.assertEqual(batch.failure_message, FAILURE_AUDIT)
        self.assertIsNone(batch.imported_at)
        self.assertEqual(batch.created_students, 0)
        self.assertEqual(batch.updated_students, 0)
        self.assertEqual(batch.created_reports, 0)
        self.assertEqual(batch.updated_applications, 0)
        self.assertEqual(self._business_counts(), before)
        self.assertFalse(OperationLog.objects.filter(action="confirm_import").exists())

    def test_backup_failure_prevents_writes_and_marks_batch_failed(self) -> None:
        batch = self._create_batch()
        before = self._business_counts()
        with patch(
            "apps.imports.import_service._create_consistent_database_backup",
            side_effect=OSError("disk full"),
        ):
            response = self.client.post(self._confirm_url(batch))
        batch.refresh_from_db()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(batch.status, ImportStatus.FAILED)
        self.assertEqual(batch.failure_message, FAILURE_BACKUP)
        self.assertEqual(self._business_counts(), before)
        self.assertTrue(artifact_path(batch.pk, ROLLBACK_FILENAME).exists())
        self.assertFalse(artifact_path(batch.pk, PRE_IMPORT_DATABASE_FILENAME).exists())

    def test_semantically_tampered_report_candidates_return_409(self) -> None:
        batch = self._create_batch()

        def duplicate_sequence(snapshot):
            snapshot["valid_rows"][0]["report_items"].append(
                dict(snapshot["valid_rows"][0]["report_items"][0])
            )
            snapshot["valid_rows"][0]["calculated_date_count"] = 2

        self._rewrite_preview(batch, duplicate_sequence)
        response = self.client.post(self._confirm_url(batch))
        batch.refresh_from_db()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(batch.status, ImportStatus.PREVIEWED)
        self.assertFalse(Student.objects.exists())

    def test_inactive_or_unknown_branch_returns_409_without_evidence_generation(self) -> None:
        self.branch.is_active = False
        self.branch.save(update_fields=["is_active"])
        batch = self._create_batch()
        response = self.client.post(self._confirm_url(batch))
        self.assertEqual(response.status_code, 409)
        self.assertFalse(artifact_path(batch.pk, ROLLBACK_FILENAME).exists())

    def test_cross_process_lock_times_out_and_recovers_after_release(self) -> None:
        with _confirmation_lock(timeout=0.1):
            with self.assertRaises(TimeoutError):
                with _confirmation_lock(timeout=0.05):
                    pass
        with _confirmation_lock(timeout=0.1):
            pass

    def test_imported_data_is_visible_to_admin_and_student_pages(self) -> None:
        batch = self._create_batch()
        self.assertEqual(self.client.post(self._confirm_url(batch)).status_code, 302)
        student = Student.objects.get(student_number="20260001")

        admin_list = self.client.get(
            reverse("students:admin_student_list"), {"student_number": "20260001"}
        )
        admin_detail = self.client.get(
            reverse("students:admin_student_detail", args=[student.pk])
        )
        self.assertContains(admin_list, "张三")
        self.assertContains(admin_detail, "20260001")
        self.assertContains(admin_detail, "2 篇")

        session = self.client.session
        session["student_id"] = student.pk
        session.save()
        profile = self.client.get(reverse("students:student_profile"))
        self.assertContains(profile, "张三")
        self.assertContains(profile, "第1次思想汇报")

    def test_zero_reported_total_overwrites_and_empty_reports_clear_old_set(self) -> None:
        student = Student.objects.create(
            name="旧姓名",
            student_number="20260001",
            branch=self.branch,
            development_stage="ACTIVIST",
        )
        summary = IdeologicalReportSummary.objects.create(
            student=student, reported_total_count=8, calculated_date_count=1
        )
        IdeologicalReport.objects.create(
            student=student,
            sequence_number=1,
            submitted_at=date(2020, 1, 1),
            source_column_name="第一次思想汇报",
        )
        result = self._result(include_warning=False)
        row = result.valid_rows[0]
        row.reported_total_count = 0
        row.calculated_date_count = 0
        row.report_items = []
        batch = self._create_batch(result)

        self.assertEqual(self.client.post(self._confirm_url(batch)).status_code, 302)
        summary.refresh_from_db()
        self.assertEqual(summary.reported_total_count, 0)
        self.assertEqual(summary.calculated_date_count, 0)
        self.assertFalse(student.ideological_reports.filter(is_active=True).exists())

    def test_new_student_with_empty_application_date_does_not_create_application(self) -> None:
        result = self._result(include_warning=False)
        result.valid_rows[0].applied_at = None
        batch = self._create_batch(result)
        self.assertEqual(self.client.post(self._confirm_url(batch)).status_code, 302)
        self.assertFalse(ApplicationRecord.objects.exists())

    def test_rollback_public_loader_rejects_tampering(self) -> None:
        batch = self._create_batch()
        self.assertEqual(self.client.post(self._confirm_url(batch)).status_code, 302)
        self.assertEqual(load_rollback_snapshot(batch)["import_batch_id"], batch.pk)
        path = artifact_path(batch.pk, ROLLBACK_FILENAME)
        path.write_bytes(path.read_bytes() + b" ")
        from apps.imports.storage import ImportEvidenceIntegrityError

        with self.assertRaises(ImportEvidenceIntegrityError):
            load_rollback_snapshot(batch)
