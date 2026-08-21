from __future__ import annotations

import hashlib
import sqlite3
from contextlib import nullcontext
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase

from apps.imports.disaster_restore import (
    DisasterRestoreError,
    REQUIRED_TABLES,
    _configured_database_path,
    restore_disaster_backup,
    verify_disaster_restore,
)
from apps.imports.models import ImportBatch, ImportStatus


def _create_database(
    path: Path,
    *,
    marker: str,
    batch_id: int | None = None,
    file_hash: str = "hash",
    status: str = ImportStatus.PREVIEWED,
) -> None:
    database = sqlite3.connect(path)
    try:
        for table in REQUIRED_TABLES - {"imports_importbatch"}:
            database.execute(f'CREATE TABLE "{table}" (id INTEGER PRIMARY KEY)')
        database.execute(
            "CREATE TABLE imports_importbatch "
            "(id INTEGER PRIMARY KEY, status TEXT NOT NULL, file_hash TEXT NOT NULL)"
        )
        database.execute("CREATE TABLE restore_marker (value TEXT NOT NULL)")
        database.execute("INSERT INTO restore_marker(value) VALUES (?)", (marker,))
        if batch_id is not None:
            database.execute(
                "INSERT INTO imports_importbatch(id, status, file_hash) VALUES (?, ?, ?)",
                (batch_id, status, file_hash),
            )
        database.commit()
    finally:
        database.close()


def _marker(path: Path) -> str:
    database = sqlite3.connect(path)
    try:
        return database.execute("SELECT value FROM restore_marker").fetchone()[0]
    finally:
        database.close()


class DisasterRestoreServiceTests(SimpleTestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.current = self.root / "current.sqlite3"
        self.backup = self.root / "pre_import.sqlite3"
        self.batch = SimpleNamespace(pk=7, file_hash="excel-sha")
        _create_database(self.current, marker="current")
        _create_database(
            self.backup,
            marker="before-import",
            batch_id=self.batch.pk,
            file_hash=self.batch.file_hash,
        )

    def _service_patches(self):
        return (
            patch(
                "apps.imports.disaster_restore._configured_database_path",
                return_value=self.current,
            ),
            patch(
                "apps.imports.disaster_restore._bound_backup_path",
                return_value=self.backup,
            ),
            patch(
                "apps.imports.disaster_restore._confirmation_lock",
                return_value=nullcontext(),
            ),
        )

    def test_verify_only_is_read_only_and_checks_batch_binding(self) -> None:
        current_before = self.current.read_bytes()
        configured, bound, _ = self._service_patches()
        with configured, bound:
            verification = verify_disaster_restore(self.batch)
        self.assertEqual(self.current.read_bytes(), current_before)
        self.assertEqual(verification.backup_path, self.backup)
        self.assertEqual(
            verification.backup_sha256,
            hashlib.sha256(self.backup.read_bytes()).hexdigest(),
        )

    def test_restore_replaces_database_and_preserves_source_and_safety_backup(self) -> None:
        source_before = self.backup.read_bytes()
        configured, bound, lock = self._service_patches()
        with configured, bound, lock:
            result = restore_disaster_backup(self.batch)
        self.assertEqual(_marker(self.current), "before-import")
        self.assertEqual(self.backup.read_bytes(), source_before)
        self.assertEqual(_marker(result.safety_backup_path), "current")
        self.assertEqual(
            result.safety_backup_sha256_path.read_text(encoding="ascii").strip(),
            hashlib.sha256(result.safety_backup_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(list(self.root.glob(".*.restore.*.tmp")), [])

    def test_batch_binding_mismatch_is_rejected_without_change(self) -> None:
        wrong_batch = SimpleNamespace(pk=8, file_hash="excel-sha")
        configured, bound, _ = self._service_patches()
        with configured, bound, self.assertRaisesRegex(
            DisasterRestoreError, "指定导入批次不匹配"
        ):
            verify_disaster_restore(wrong_batch)
        self.assertEqual(_marker(self.current), "current")

    def test_corrupt_backup_is_rejected_without_change(self) -> None:
        self.backup.write_bytes(b"not sqlite")
        configured, bound, _ = self._service_patches()
        with configured, bound, self.assertRaises(DisasterRestoreError):
            verify_disaster_restore(self.batch)
        self.assertEqual(_marker(self.current), "current")

    def test_safety_backup_failure_prevents_replacement(self) -> None:
        configured, bound, lock = self._service_patches()
        with configured, bound, lock, patch(
            "apps.imports.disaster_restore._backup_current_database",
            side_effect=DisasterRestoreError("backup failed"),
        ), self.assertRaises(DisasterRestoreError):
            restore_disaster_backup(self.batch)
        self.assertEqual(_marker(self.current), "current")

    def test_atomic_replace_failure_keeps_current_database(self) -> None:
        configured, bound, lock = self._service_patches()
        real_replace = __import__("os").replace

        def fail_target_replace(source: Path, destination: Path) -> None:
            if Path(destination) == self.current:
                raise OSError("replace failed")
            real_replace(source, destination)

        with configured, bound, lock, patch(
            "apps.imports.disaster_restore.os.replace", side_effect=fail_target_replace
        ), self.assertRaises(DisasterRestoreError):
            restore_disaster_backup(self.batch)
        self.assertEqual(_marker(self.current), "current")
        self.assertEqual(list(self.root.glob(".*.restore.*.tmp")), [])

    def test_sqlite_sidecar_refuses_restore_after_safety_backup(self) -> None:
        Path(f"{self.current}-wal").write_bytes(b"stale")
        configured, bound, lock = self._service_patches()
        with configured, bound, lock, self.assertRaisesRegex(
            DisasterRestoreError, "边车文件"
        ):
            restore_disaster_backup(self.batch)
        self.assertEqual(_marker(self.current), "current")

    def test_post_replace_failure_automatically_restores_current_database(self) -> None:
        configured, bound, lock = self._service_patches()
        from apps.imports import disaster_restore

        real_verify = disaster_restore._verify_sqlite_database
        target_verifications = 0

        def fail_first_post_replace(path: Path, require_batch: object) -> None:
            nonlocal target_verifications
            if Path(path) == self.current and require_batch is not None:
                target_verifications += 1
                if target_verifications == 1:
                    raise DisasterRestoreError("post replace failure")
            real_verify(path, require_batch)

        with configured, bound, lock, patch(
            "apps.imports.disaster_restore._verify_sqlite_database",
            side_effect=fail_first_post_replace,
        ), self.assertRaisesRegex(DisasterRestoreError, "自动恢复"):
            restore_disaster_backup(self.batch)
        self.assertEqual(_marker(self.current), "current")

    def test_non_sqlite_database_is_rejected(self) -> None:
        with patch.dict(
            settings.DATABASES,
            {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "db"}},
            clear=True,
        ), self.assertRaisesRegex(DisasterRestoreError, "仅支持SQLite"):
            _configured_database_path()

    def test_in_memory_sqlite_is_rejected(self) -> None:
        with patch.dict(
            settings.DATABASES,
            {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            clear=True,
        ), self.assertRaisesRegex(DisasterRestoreError, "内存SQLite"):
            _configured_database_path()


class RestoreImportBackupCommandTests(TestCase):
    def setUp(self) -> None:
        self.batch = ImportBatch.objects.create(
            batch_label="restore",
            original_filename="restore.xlsx",
            file_hash="hash",
            status=ImportStatus.SUCCESS,
        )

    def test_default_mode_verifies_without_restoring(self) -> None:
        output = StringIO()
        verification = SimpleNamespace(
            batch_id=self.batch.pk,
            backup_path=Path("backup.sqlite3"),
            backup_sha256="abc",
        )
        with patch(
            "apps.imports.management.commands.restore_import_backup.verify_disaster_restore",
            return_value=verification,
        ) as verify, patch(
            "apps.imports.management.commands.restore_import_backup.restore_disaster_backup"
        ) as restore:
            call_command("restore_import_backup", batch_id=self.batch.pk, stdout=output)
        verify.assert_called_once()
        restore.assert_not_called()
        self.assertIn("未修改数据库", output.getvalue())

    def test_confirm_requires_maintenance_mode(self) -> None:
        with self.assertRaisesRegex(CommandError, "--maintenance-mode"):
            call_command("restore_import_backup", batch_id=self.batch.pk, confirm=True)

    def test_confirm_with_maintenance_mode_executes_restore(self) -> None:
        output = StringIO()
        result = SimpleNamespace(
            verification=SimpleNamespace(batch_id=self.batch.pk),
            safety_backup_path=Path("safety.sqlite3"),
            safety_backup_sha256_path=Path("safety.sha256"),
        )
        with patch(
            "apps.imports.management.commands.restore_import_backup.restore_disaster_backup",
            return_value=result,
        ) as restore:
            call_command(
                "restore_import_backup",
                batch_id=self.batch.pk,
                confirm=True,
                maintenance_mode=True,
                stdout=output,
            )
        restore.assert_called_once_with(self.batch)
        self.assertIn("灾难恢复完成", output.getvalue())

    def test_mutually_exclusive_modes_are_rejected(self) -> None:
        with self.assertRaisesRegex(CommandError, "不能同时使用"):
            call_command(
                "restore_import_backup",
                batch_id=self.batch.pk,
                verify_only=True,
                confirm=True,
                maintenance_mode=True,
            )

    def test_missing_batch_is_rejected(self) -> None:
        with self.assertRaisesRegex(CommandError, "批次不存在"):
            call_command("restore_import_backup", batch_id=999999)
