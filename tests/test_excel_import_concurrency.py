from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from tempfile import TemporaryDirectory
from threading import Barrier

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections
from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse

from apps.accounts.models import AdminRole, AdminUser
from apps.audit.models import OperationLog
from apps.imports.datatypes import ParseResult, ParsedReportItem, ParsedStudentRow, SheetResult
from apps.imports.models import ImportBatch, ImportStatus
from apps.imports.snapshots import ROLLBACK_FILENAME, build_preview_snapshot, write_preview_snapshot
from apps.imports.storage import artifact_path, store_uploaded_file
from apps.students.models import PartyBranch, Student


class ConfirmImportConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self) -> None:
        self.temp_media = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.temp_media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.temp_media.cleanup)
        PartyBranch.objects.create(code="MINGLI", name="明理党支部")
        self.admin_a = AdminUser.objects.create_user(
            username="concurrent-a", password="pass12345", role=AdminRole.DATA_ADMIN
        )
        self.admin_b = AdminUser.objects.create_user(
            username="concurrent-b", password="pass12345", role=AdminRole.DATA_ADMIN
        )

    def _create_batch(self, label: str) -> ImportBatch:
        batch = ImportBatch.objects.create(
            batch_label=label,
            original_filename=f"{label}.xlsx",
            imported_by=self.admin_a,
        )
        uploaded = SimpleUploadedFile(f"{label}.xlsx", label.encode("utf-8"))
        stored = store_uploaded_file(batch, uploaded)
        batch.stored_file.name = stored.relative_name
        batch.file_hash = stored.sha256
        batch.total_sheets = 1
        batch.success_sheets = 1
        batch.total_rows = 1
        batch.success_rows = 1
        batch.save()
        row = ParsedStudentRow(
            sheet_name="明理党支部",
            excel_row_number=3,
            branch_code="MINGLI",
            branch_name="明理党支部",
            name=f"学生{label}",
            student_number="20260001",
            development_stage="ACTIVIST",
            position="",
            applied_at=date(2025, 1, 1),
            calculated_date_count=1,
            report_items=[ParsedReportItem(1, date(2025, 2, 1), "第一次思想汇报")],
        )
        result = ParseResult(
            total_sheets=1,
            success_sheets=1,
            total_rows=1,
            success_rows=1,
            valid_rows=[row],
            sheet_results=[
                SheetResult(
                    "明理党支部", "MINGLI", "明理党支部", "success", 1, 1, 0, 0
                )
            ],
        )
        write_preview_snapshot(batch, build_preview_snapshot(batch, result))
        return batch

    def _clients(self) -> tuple[Client, Client]:
        first = Client()
        second = Client()
        first.force_login(self.admin_a)
        second.force_login(self.admin_b)
        return first, second

    @staticmethod
    def _post_at_barrier(client: Client, url: str, barrier: Barrier) -> int:
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            return client.post(url).status_code
        finally:
            close_old_connections()

    def test_same_batch_near_simultaneous_confirm_has_one_success(self) -> None:
        batch = self._create_batch("same")
        clients = self._clients()
        barrier = Barrier(2)
        url = reverse("imports:confirm", args=[batch.pk])
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(
                pool.map(
                    lambda client: self._post_at_barrier(client, url, barrier),
                    clients,
                )
            )
        batch.refresh_from_db()
        self.assertEqual(sorted(statuses), [302, 409])
        self.assertEqual(batch.status, ImportStatus.SUCCESS)
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(OperationLog.objects.filter(action="confirm_import").count(), 1)

    def test_different_batches_are_serialized_and_second_snapshot_sees_first(self) -> None:
        first_batch = self._create_batch("first")
        second_batch = self._create_batch("second")
        clients = self._clients()
        barrier = Barrier(2)
        urls = (
            reverse("imports:confirm", args=[first_batch.pk]),
            reverse("imports:confirm", args=[second_batch.pk]),
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(self._post_at_barrier, client, url, barrier)
                for client, url in zip(clients, urls, strict=True)
            ]
            statuses = [future.result(timeout=20) for future in futures]
        self.assertEqual(statuses, [302, 302])
        snapshots = [
            json.loads(artifact_path(batch.pk, ROLLBACK_FILENAME).read_text(encoding="utf-8"))
            for batch in (first_batch, second_batch)
        ]
        existed_values = sorted(
            snapshot["students"][0]["student_existed_before"] for snapshot in snapshots
        )
        self.assertEqual(existed_values, [False, True])
        self.assertEqual(OperationLog.objects.filter(action="confirm_import").count(), 2)
