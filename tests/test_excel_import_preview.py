from __future__ import annotations

import hashlib
import json
from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from openpyxl import Workbook

from apps.accounts.models import AdminRole, AdminUser
from apps.audit.models import OperationLog
from apps.imports.datatypes import (
    ParseError,
    ParseResult,
    ParseWarning,
    ParsedReportItem,
    ParsedStudentRow,
    SheetResult,
)
from apps.imports.forms import MAX_EXCEL_UPLOAD_SIZE
from apps.imports.models import ImportBatch, ImportErrorRecord, ImportStatus, ImportWarningRecord
from apps.imports.snapshots import PREVIEW_FILENAME, PREVIEW_HASH_FILENAME
from apps.imports.storage import (
    ImportEvidenceIntegrityError,
    artifact_path,
    sanitize_original_filename,
    verified_original_path,
)
from apps.materials.models import ApplicationRecord, IdeologicalReport, IdeologicalReportSummary
from apps.students.models import DevelopmentStage, PartyBranch, Student


class ExcelPreviewTestCase(TestCase):
    def setUp(self) -> None:
        self.temp_media = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.temp_media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.temp_media.cleanup)

        self.viewer = AdminUser.objects.create_user(
            username="preview-viewer",
            password="testpass123",
            role=AdminRole.VIEWER_ADMIN,
        )
        self.data_admin = AdminUser.objects.create_user(
            username="preview-data",
            password="testpass123",
            role=AdminRole.DATA_ADMIN,
        )

    def _login_data_admin(self) -> None:
        self.client.force_login(self.data_admin)

    def _upload_file(self, name: str = "members.xlsx", content: bytes = b"xlsx-content"):
        return SimpleUploadedFile(
            name,
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def _warning(self) -> ParseWarning:
        return ParseWarning(
            code="REPORT_COUNT_MISMATCH",
            message="填报数与日期数不一致",
            sheet_name="明理党支部",
            excel_row_number=3,
            student_name="张三",
            student_number="20260001",
            field_name="reported_total_count",
            source_value="2",
            parsed_value="1",
        )

    def _result(self, *, student_number: str = "20260001", include_warning: bool = True) -> ParseResult:
        warning = self._warning()
        row = ParsedStudentRow(
            sheet_name="明理党支部",
            excel_row_number=3,
            branch_code="MINGLI",
            branch_name="明理党支部",
            name="张三",
            student_number=student_number,
            development_stage="ACTIVIST",
            position="班长",
            applied_at=date(2025, 1, 2),
            reported_total_count=2,
            calculated_date_count=1,
            report_items=[
                ParsedReportItem(
                    sequence_number=1,
                    submitted_at=date(2025, 2, 3),
                    source_column_name="第一次思想汇报",
                )
            ],
            warnings=[warning] if include_warning else [],
        )
        return ParseResult(
            total_sheets=1,
            success_sheets=1,
            failed_sheets=0,
            total_rows=1,
            success_rows=1,
            skipped_rows=0,
            warning_rows=1 if include_warning else 0,
            valid_rows=[row],
            warnings=[warning] if include_warning else [],
            sheet_results=[
                SheetResult(
                    sheet_name="明理党支部",
                    branch_code="MINGLI",
                    branch_name="明理党支部",
                    status="success",
                    total_rows=1,
                    valid_row_count=1,
                    error_count=0,
                    warning_count=1 if include_warning else 0,
                )
            ],
        )

    def _post_upload(
        self,
        result: ParseResult | None = None,
        *,
        name: str = "members.xlsx",
        content: bytes = b"xlsx-content",
    ):
        result = result if result is not None else self._result()
        with patch("apps.imports.views.parse_workbook", return_value=result):
            return self.client.post(
                reverse("imports:upload"),
                {"excel_file": self._upload_file(name, content)},
            )


class PermissionAndMethodTests(ExcelPreviewTestCase):
    def test_anonymous_is_redirected_for_all_protected_entries(self) -> None:
        batch = ImportBatch.objects.create(batch_label="b", original_filename="a.xlsx")
        urls = (
            reverse("imports:upload"),
            reverse("imports:preview", args=[batch.pk]),
            reverse("imports:history"),
            reverse("imports:batch_detail", args=[batch.pk]),
            reverse("imports:download_file", args=[batch.pk]),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("accounts:admin_login"), response.url)

    def test_viewer_can_read_history_and_detail_but_not_sensitive_entries(self) -> None:
        batch = ImportBatch.objects.create(batch_label="b", original_filename="a.xlsx")
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(reverse("imports:history")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("imports:batch_detail", args=[batch.pk])).status_code,
            200,
        )
        self.assertEqual(self.client.get(reverse("imports:upload")).status_code, 403)
        self.assertEqual(
            self.client.get(reverse("imports:preview", args=[batch.pk])).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse("imports:download_file", args=[batch.pk])).status_code,
            403,
        )

    def test_data_admin_can_open_upload(self) -> None:
        self._login_data_admin()
        response = self.client.get(reverse("imports:upload"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "上传并生成预览")

    def test_upload_rejects_put_and_read_entries_reject_post(self) -> None:
        batch = ImportBatch.objects.create(batch_label="b", original_filename="a.xlsx")
        self._login_data_admin()
        self.assertEqual(self.client.put(reverse("imports:upload")).status_code, 405)
        for url in (
            reverse("imports:preview", args=[batch.pk]),
            reverse("imports:history"),
            reverse("imports:batch_detail", args=[batch.pk]),
            reverse("imports:download_file", args=[batch.pk]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 405)

    def test_upload_post_requires_csrf(self) -> None:
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.data_admin)
        response = csrf_client.post(
            reverse("imports:upload"),
            {"excel_file": self._upload_file()},
        )
        self.assertEqual(response.status_code, 403)


class UploadValidationTests(ExcelPreviewTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._login_data_admin()

    def test_accepts_case_insensitive_xlsx_extension(self) -> None:
        response = self._post_upload(name="MEMBERS.XLSX")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ImportBatch.objects.count(), 1)

    def test_rejects_wrong_and_double_extension(self) -> None:
        for filename in ("members.xls", "members.xlsx.exe", "members.zip"):
            with self.subTest(filename=filename):
                response = self.client.post(
                    reverse("imports:upload"),
                    {"excel_file": self._upload_file(filename)},
                )
                self.assertEqual(response.status_code, 400)
        self.assertEqual(ImportBatch.objects.count(), 0)

    def test_rejects_empty_file(self) -> None:
        response = self.client.post(
            reverse("imports:upload"),
            {"excel_file": self._upload_file(content=b"")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ImportBatch.objects.count(), 0)

    def test_allows_exact_size_limit(self) -> None:
        response = self._post_upload(content=b"x" * MAX_EXCEL_UPLOAD_SIZE)
        self.assertEqual(response.status_code, 302)

    def test_rejects_one_byte_over_size_limit_without_calling_parser(self) -> None:
        with patch("apps.imports.views.parse_workbook") as parser_mock:
            response = self.client.post(
                reverse("imports:upload"),
                {"excel_file": self._upload_file(content=b"x" * (MAX_EXCEL_UPLOAD_SIZE + 1))},
            )
        self.assertEqual(response.status_code, 400)
        parser_mock.assert_not_called()
        self.assertEqual(ImportBatch.objects.count(), 0)

    def test_filename_sanitizer_removes_paths_and_control_characters(self) -> None:
        self.assertEqual(sanitize_original_filename("../../secret.xlsx"), "secret.xlsx")
        self.assertEqual(sanitize_original_filename("..\\secret.xlsx"), "secret.xlsx")
        self.assertEqual(sanitize_original_filename("bad\x00name.xlsx"), "badname.xlsx")


class EvidenceCreationTests(ExcelPreviewTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._login_data_admin()

    def test_upload_creates_random_file_hash_and_snapshot_evidence(self) -> None:
        content = b"same workbook bytes"
        response = self._post_upload(content=content)
        self.assertEqual(response.status_code, 302)
        batch = ImportBatch.objects.get()

        original_path = verified_original_path(batch)
        self.assertTrue(original_path.name.startswith("original_"))
        self.assertEqual(original_path.suffix, ".xlsx")
        self.assertEqual(batch.file_hash, hashlib.sha256(content).hexdigest())
        self.assertTrue(artifact_path(batch.pk, PREVIEW_FILENAME).is_file())
        self.assertTrue(artifact_path(batch.pk, PREVIEW_HASH_FILENAME).is_file())

        payload = artifact_path(batch.pk, PREVIEW_FILENAME).read_bytes()
        snapshot_hash = artifact_path(batch.pk, PREVIEW_HASH_FILENAME).read_text(encoding="ascii")
        self.assertEqual(hashlib.sha256(payload).hexdigest(), snapshot_hash)
        snapshot = json.loads(payload)
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertEqual(snapshot["import_batch_id"], batch.pk)
        self.assertEqual(snapshot["file_sha256"], batch.file_hash)
        self.assertEqual(snapshot["valid_rows"][0]["applied_at"], "2025-01-02")
        self.assertEqual(
            snapshot["valid_rows"][0]["report_items"][0]["submitted_at"],
            "2025-02-03",
        )

    def test_same_original_name_never_overwrites(self) -> None:
        self._post_upload(content=b"first")
        self._post_upload(content=b"second")
        batches = list(ImportBatch.objects.order_by("id"))
        self.assertEqual(len(batches), 2)
        self.assertNotEqual(batches[0].stored_file.name, batches[1].stored_file.name)
        self.assertEqual(verified_original_path(batches[0]).read_bytes(), b"first")
        self.assertEqual(verified_original_path(batches[1]).read_bytes(), b"second")

    def test_parse_records_and_statistics_are_mapped(self) -> None:
        result = self._result()
        result.errors.append(
            ParseError(
                code="ROW_INVALID_STAGE",
                message="阶段无效",
                sheet_name="明理党支部",
                excel_row_number=4,
                student_name="李四",
                student_number="20260002",
                field_name="development_stage",
            )
        )
        result.total_rows = 2
        result.skipped_rows = 1
        result.sheet_results[0].total_rows = 2
        result.sheet_results[0].error_count = 1
        self._post_upload(result)
        batch = ImportBatch.objects.get()
        self.assertEqual(batch.total_rows, 2)
        self.assertEqual(batch.success_rows, 1)
        self.assertEqual(batch.skipped_rows, 1)
        self.assertEqual(batch.invalid_stage_rows, 1)
        self.assertEqual(batch.count_mismatch_rows, 1)
        self.assertEqual(ImportErrorRecord.objects.get().excel_row_number, 4)
        self.assertEqual(ImportWarningRecord.objects.get().warning_code, "REPORT_COUNT_MISMATCH")

    def test_missing_row_number_rejects_batch_instead_of_inventing_one(self) -> None:
        result = self._result(include_warning=False)
        result.errors.append(
            ParseError(
                code="SHEET_ERROR",
                message="工作表错误",
                sheet_name="明理党支部",
                excel_row_number=None,
            )
        )
        response = self._post_upload(result)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ImportBatch.objects.count(), 0)
        self.assertFalse(list(Path(self.temp_media.name).glob("imports/batch_*")))

    def test_parser_system_error_rolls_back_database_files_and_audit(self) -> None:
        with patch("apps.imports.views.parse_workbook", side_effect=ValueError("broken workbook")):
            response = self.client.post(
                reverse("imports:upload"),
                {"excel_file": self._upload_file()},
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ImportBatch.objects.count(), 0)
        self.assertEqual(OperationLog.objects.filter(action="upload_excel").count(), 0)
        self.assertFalse(list(Path(self.temp_media.name).glob("imports/batch_*")))

    def test_successful_upload_writes_one_audit_record(self) -> None:
        self._post_upload()
        batch = ImportBatch.objects.get()
        log = OperationLog.objects.get(action="upload_excel")
        self.assertEqual(log.operator, self.data_admin)
        self.assertEqual(log.target_type, "ImportBatch")
        self.assertEqual(log.target_id, str(batch.pk))


class PreviewIntegrityTests(ExcelPreviewTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._login_data_admin()
        self._post_upload()
        self.batch = ImportBatch.objects.get()
        self.preview_url = reverse("imports:preview", args=[self.batch.pk])

    def test_preview_displays_snapshot_and_records(self) -> None:
        response = self.client.get(self.preview_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "原文件与服务端preview快照完整性校验通过")
        self.assertContains(response, "2025年1月2日")
        self.assertContains(response, "REPORT_COUNT_MISMATCH")

    def test_confirm_button_is_visible_for_confirmable_preview(self) -> None:
        response = self.client.get(self.preview_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "确认正式导入")
        self.assertContains(
            response,
            f'action="{reverse("imports:confirm", args=[self.batch.pk])}"',
            html=False,
        )
        self.assertNotContains(response, "正式确认入口将在PR2实现")

    def test_confirm_button_is_hidden_after_batch_leaves_previewed_status(self) -> None:
        self.batch.status = ImportStatus.SUCCESS
        self.batch.save(update_fields=["status"])

        response = self.client.get(self.preview_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "确认正式导入")
        self.assertContains(response, "不能再次确认导入")

    def test_original_file_tampering_rejects_preview(self) -> None:
        original_path = Path(self.temp_media.name) / self.batch.stored_file.name
        original_path.write_bytes(b"tampered")
        response = self.client.get(self.preview_url)
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "完整性校验失败", status_code=409)

    def test_preview_json_tampering_is_rejected(self) -> None:
        artifact_path(self.batch.pk, PREVIEW_FILENAME).write_text("{}", encoding="utf-8")
        response = self.client.get(self.preview_url)
        self.assertEqual(response.status_code, 409)

    def test_preview_schema_or_batch_mismatch_is_rejected_even_with_matching_hash(self) -> None:
        preview_path = artifact_path(self.batch.pk, PREVIEW_FILENAME)
        hash_path = artifact_path(self.batch.pk, PREVIEW_HASH_FILENAME)
        snapshot = json.loads(preview_path.read_text(encoding="utf-8"))
        snapshot["import_batch_id"] = self.batch.pk + 1
        payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        preview_path.write_bytes(payload)
        hash_path.write_text(hashlib.sha256(payload).hexdigest(), encoding="ascii")
        response = self.client.get(self.preview_url)
        self.assertEqual(response.status_code, 409)

    def test_missing_snapshot_returns_404(self) -> None:
        artifact_path(self.batch.pk, PREVIEW_FILENAME).unlink()
        response = self.client.get(self.preview_url)
        self.assertEqual(response.status_code, 404)

    def test_duplicate_student_number_is_visible_and_not_confirmable(self) -> None:
        ImportBatch.objects.all().delete()
        result = self._result()
        duplicate = self._result().valid_rows[0]
        duplicate.name = "另一个姓名"
        result.valid_rows.append(duplicate)
        result.success_rows = 2
        result.total_rows = 2
        result.sheet_results[0].total_rows = 2
        result.sheet_results[0].valid_row_count = 2
        response = self._post_upload(result)
        batch = ImportBatch.objects.get()
        preview_response = self.client.get(reverse("imports:preview", args=[batch.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertContains(preview_response, "出现多次")
        self.assertNotContains(preview_response, "确认正式导入")
        snapshot = json.loads(artifact_path(batch.pk, PREVIEW_FILENAME).read_text(encoding="utf-8"))
        self.assertFalse(snapshot["can_confirm"])

    def test_empty_valid_rows_still_forms_readable_preview(self) -> None:
        ImportBatch.objects.all().delete()
        empty = ParseResult(
            total_sheets=1,
            success_sheets=1,
            sheet_results=[SheetResult("明理党支部", "MINGLI", "明理党支部", "success")],
        )
        response = self._post_upload(empty)
        batch = ImportBatch.objects.get()
        preview_response = self.client.get(reverse("imports:preview", args=[batch.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(preview_response.status_code, 200)
        self.assertContains(preview_response, "没有有效候选行")
        self.assertNotContains(preview_response, "确认正式导入")


class BusinessTableZeroWriteTests(ExcelPreviewTestCase):
    def test_upload_and_preview_leave_all_four_business_tables_unchanged(self) -> None:
        branch = PartyBranch.objects.create(code="MINGLI", name="明理党支部")
        student = Student.objects.create(
            name="原学生",
            student_number="20250001",
            branch=branch,
            development_stage=DevelopmentStage.ACTIVIST,
        )
        ApplicationRecord.objects.create(student=student, applied_at=date(2024, 1, 1))
        IdeologicalReportSummary.objects.create(
            student=student,
            reported_total_count=1,
            calculated_date_count=1,
        )
        IdeologicalReport.objects.create(
            student=student,
            sequence_number=1,
            submitted_at=date(2024, 2, 1),
            source_column_name="第一次思想汇报",
        )
        before = {
            "students": list(Student.objects.values()),
            "applications": list(ApplicationRecord.objects.values()),
            "summaries": list(IdeologicalReportSummary.objects.values()),
            "reports": list(IdeologicalReport.objects.values()),
        }

        self._login_data_admin()
        upload_response = self._post_upload()
        batch = ImportBatch.objects.get()
        preview_response = self.client.get(reverse("imports:preview", args=[batch.pk]))
        self.assertEqual(upload_response.status_code, 302)
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(before["students"], list(Student.objects.values()))
        self.assertEqual(before["applications"], list(ApplicationRecord.objects.values()))
        self.assertEqual(before["summaries"], list(IdeologicalReportSummary.objects.values()))
        self.assertEqual(before["reports"], list(IdeologicalReport.objects.values()))


class HistoryDetailDownloadTests(ExcelPreviewTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._login_data_admin()
        self._post_upload(content=b"download-content")
        self.first_batch = ImportBatch.objects.get()

    def test_history_uses_model_default_newest_first_order(self) -> None:
        self._post_upload(content=b"second")
        newest = ImportBatch.objects.order_by("-id").first()
        response = self.client.get(reverse("imports:history"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["batches"][0], newest)

    def test_detail_and_missing_batch(self) -> None:
        response = self.client.get(reverse("imports:batch_detail", args=[self.first_batch.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.first_batch.file_hash)
        self.assertEqual(
            self.client.get(reverse("imports:batch_detail", args=[999999])).status_code,
            404,
        )

    def test_data_admin_downloads_verified_original_with_safe_name(self) -> None:
        response = self.client.get(reverse("imports:download_file", args=[self.first_batch.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"download-content")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertNotIn(str(Path(self.temp_media.name)), response["Content-Disposition"])

    def test_missing_file_returns_404_and_tampered_file_returns_409(self) -> None:
        original_path = verified_original_path(self.first_batch)
        original_path.unlink()
        self.assertEqual(
            self.client.get(reverse("imports:download_file", args=[self.first_batch.pk])).status_code,
            404,
        )
        original_path.write_bytes(b"tampered")
        self.assertEqual(
            self.client.get(reverse("imports:download_file", args=[self.first_batch.pk])).status_code,
            409,
        )

    def test_path_escape_in_stored_file_is_rejected(self) -> None:
        self.first_batch.stored_file.name = "imports/escape.xlsx"
        self.first_batch.save(update_fields=["stored_file"])
        with self.assertRaises(ImportEvidenceIntegrityError):
            verified_original_path(self.first_batch)


class RealParserIntegrationTests(ExcelPreviewTestCase):
    def test_uploaded_workbook_is_processed_by_the_unified_parser(self) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "明理党支部"
        sheet.append(["基本信息", "基本信息", "基本信息", "材料"])
        sheet.append(["姓名", "学号", "发展阶段", "申请入党时间"])
        sheet.append(["张三", "20260001", "入党积极分子", "2025/01/02"])
        buffer = BytesIO()
        workbook.save(buffer)
        workbook.close()

        self._login_data_admin()
        response = self.client.post(
            reverse("imports:upload"),
            {"excel_file": self._upload_file(content=buffer.getvalue())},
        )
        self.assertEqual(response.status_code, 302)
        batch = ImportBatch.objects.get()
        self.assertEqual(batch.total_sheets, 1)
        self.assertEqual(batch.success_rows, 1)
        snapshot = json.loads(artifact_path(batch.pk, PREVIEW_FILENAME).read_text(encoding="utf-8"))
        self.assertEqual(snapshot["valid_rows"][0]["student_number"], "20260001")
