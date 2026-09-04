from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

from django.conf import settings
from django.db import connection, transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.audit.services import record_operation_log
from apps.imports.models import ImportBatch, ImportStatus
from apps.imports.snapshots import (
    PREVIEW_HASH_FILENAME,
    ROLLBACK_FILENAME,
    ROLLBACK_HASH_FILENAME,
    ROLLBACK_SCHEMA_VERSION,
    load_preview_snapshot,
    load_rollback_snapshot,
)
from apps.imports.storage import (
    ImportEvidenceIntegrityError,
    ImportEvidenceNotFound,
    artifact_path,
)
from apps.materials.models import ApplicationRecord, IdeologicalReport, IdeologicalReportSummary
from apps.students.models import DevelopmentStage, PartyBranch, Student


PRE_IMPORT_DATABASE_FILENAME = "pre_import.sqlite3"
CONFIRM_LOCK_TIMEOUT_SECONDS = 5.0
FAILURE_EVIDENCE = "IMPORT_EVIDENCE_GENERATION_FAILED"
FAILURE_BACKUP = "IMPORT_DATABASE_BACKUP_FAILED"
FAILURE_TRANSACTION = "IMPORT_TRANSACTION_FAILED"
FAILURE_AUDIT = "IMPORT_AUDIT_FAILED"
logger = logging.getLogger(__name__)


class ConfirmImportConflict(Exception):
    """确认请求与批次状态、候选或证据发生冲突。"""


class ConfirmImportFailed(Exception):
    """保护证据生成或正式事务执行失败。"""


def confirm_import(request: HttpRequest, batch_id: int) -> ImportBatch:
    """在单一串行窗口内生成证据并原子写入全部有效候选。"""
    failure_code = FAILURE_EVIDENCE
    try:
        with _confirmation_lock():
            batch = _load_previewed_batch(batch_id)
            try:
                snapshot = load_preview_snapshot(batch)
            except (ImportEvidenceNotFound, ImportEvidenceIntegrityError) as exc:
                raise ConfirmImportConflict(str(exc)) from exc
            _validate_confirmable_candidates(snapshot)

            rollback_snapshot = _build_rollback_snapshot(batch, snapshot)
            _write_json_evidence(
                batch,
                rollback_snapshot,
                filename=ROLLBACK_FILENAME,
                hash_filename=ROLLBACK_HASH_FILENAME,
            )
            failure_code = FAILURE_BACKUP
            _create_consistent_database_backup(batch)

            failure_code = FAILURE_TRANSACTION
            try:
                with transaction.atomic():
                    locked_batch = ImportBatch.objects.select_for_update().get(pk=batch.pk)
                    if locked_batch.status != ImportStatus.PREVIEWED:
                        raise ConfirmImportConflict("当前批次状态不允许确认。")

                    try:
                        verified_snapshot = load_preview_snapshot(locked_batch)
                    except (ImportEvidenceNotFound, ImportEvidenceIntegrityError) as exc:
                        raise ConfirmImportConflict(str(exc)) from exc
                    _validate_confirmable_candidates(verified_snapshot)
                    if verified_snapshot != snapshot:
                        raise ConfirmImportConflict("确认窗口内预览证据发生变化。")
                    try:
                        verified_rollback = load_rollback_snapshot(locked_batch)
                    except (ImportEvidenceNotFound, ImportEvidenceIntegrityError) as exc:
                        raise ConfirmImportConflict(str(exc)) from exc
                    if verified_rollback != rollback_snapshot:
                        raise ConfirmImportConflict("确认窗口内回滚快照证据发生变化。")
                    _verify_sqlite_backup(
                        artifact_path(locked_batch.pk, PRE_IMPORT_DATABASE_FILENAME)
                    )

                    _apply_candidates(locked_batch, verified_snapshot["valid_rows"])
                    locked_batch.status = ImportStatus.SUCCESS
                    locked_batch.imported_at = timezone.now()
                    locked_batch.imported_by = request.user
                    locked_batch.save()
                    failure_code = FAILURE_AUDIT
                    record_operation_log(
                        request,
                        action="confirm_import",
                        target_type="ImportBatch",
                        target_id=str(locked_batch.pk),
                        description="确认Excel正式导入",
                    )
                return locked_batch
            except ConfirmImportConflict:
                raise
            except Exception as exc:
                _mark_batch_failed(batch.pk, failure_code)
                raise ConfirmImportFailed("正式导入失败，业务数据已完整回滚。") from exc
    except TimeoutError as exc:
        raise ConfirmImportConflict("已有导入任务正在执行，请稍后重试。") from exc
    except ConfirmImportConflict:
        raise
    except ConfirmImportFailed:
        raise
    except Exception as exc:
        _mark_batch_failed(batch_id, failure_code)
        raise ConfirmImportFailed("导入保护证据生成失败，未写入业务数据。") from exc


def _load_previewed_batch(batch_id: int) -> ImportBatch:
    try:
        batch = ImportBatch.objects.get(pk=batch_id)
    except ImportBatch.DoesNotExist:
        raise
    if batch.status != ImportStatus.PREVIEWED:
        raise ConfirmImportConflict("当前批次状态不允许确认；重复请求不会再次执行导入。")
    return batch


def _validate_confirmable_candidates(snapshot: dict[str, Any]) -> None:
    if not snapshot["can_confirm"]:
        if snapshot["conflicts"]:
            raise ConfirmImportConflict("批次存在重复学号冲突，不能确认导入。")
        raise ConfirmImportConflict("批次没有有效候选数据，不能确认导入。")

    active_branches = set(
        PartyBranch.objects.filter(is_active=True).values_list("code", flat=True)
    )
    allowed_stages = set(DevelopmentStage.values)
    for row in snapshot["valid_rows"]:
        if row["branch_code"] not in active_branches:
            raise ConfirmImportConflict(f"支部代码不可用：{row['branch_code']}")
        if row["development_stage"] not in allowed_stages:
            raise ConfirmImportConflict(f"发展阶段不可用：{row['development_stage']}")
        sequences = [item["sequence_number"] for item in row["report_items"]]
        submitted_dates = [item["submitted_at"] for item in row["report_items"]]
        if len(sequences) != len(set(sequences)):
            raise ConfirmImportConflict("同一学生存在重复思想汇报次数。")
        if len(submitted_dates) != len(set(submitted_dates)):
            raise ConfirmImportConflict("同一学生存在重复思想汇报日期。")
        if row["calculated_date_count"] != len(submitted_dates):
            raise ConfirmImportConflict("思想汇报计算数量与有效明细不一致。")


def _build_rollback_snapshot(batch: ImportBatch, preview: dict[str, Any]) -> dict[str, Any]:
    preview_sha256 = artifact_path(batch.pk, PREVIEW_HASH_FILENAME).read_text(
        encoding="ascii"
    ).strip()
    numbers = sorted(row["student_number"] for row in preview["valid_rows"])
    students_by_number = {
        student.student_number: student
        for student in Student.objects.filter(student_number__in=numbers)
    }
    student_ids = [student.pk for student in students_by_number.values()]
    applications = {
        record.student_id: record
        for record in ApplicationRecord.objects.filter(student_id__in=student_ids)
    }
    summaries = {
        summary.student_id: summary
        for summary in IdeologicalReportSummary.objects.filter(student_id__in=student_ids)
    }
    reports_by_student: dict[int, list[IdeologicalReport]] = {}
    for report in IdeologicalReport.objects.filter(
        student_id__in=student_ids, is_active=True
    ).order_by("student_id", "sequence_number", "pk"):
        reports_by_student.setdefault(report.student_id, []).append(report)
    records = [
        _serialize_student_before(
            number,
            students_by_number.get(number),
            applications,
            summaries,
            reports_by_student,
        )
        for number in numbers
    ]
    return {
        "schema_version": ROLLBACK_SCHEMA_VERSION,
        "import_batch_id": batch.pk,
        "preview_sha256": preview_sha256,
        "created_at": timezone.now().isoformat(),
        "record_count": len(records),
        "students": records,
    }


def _serialize_student_before(
    student_number: str,
    student: Student | None,
    applications: dict[int, ApplicationRecord],
    summaries: dict[int, IdeologicalReportSummary],
    reports_by_student: dict[int, list[IdeologicalReport]],
) -> dict[str, Any]:
    if student is None:
        return {
            "student_number": student_number,
            "student_existed_before": False,
            "student": None,
            "application_record": None,
            "report_summary": None,
            "active_reports": [],
        }

    application = applications.get(student.pk)
    summary = summaries.get(student.pk)
    reports = reports_by_student.get(student.pk, [])
    return {
        "student_number": student_number,
        "student_existed_before": True,
        "student": {
            "id": student.pk,
            "name": student.name,
            "student_number": student.student_number,
            "branch_id": student.branch_id,
            "development_stage": student.development_stage,
            "position": student.position,
            "status": student.status,
            "source_import_batch_id": student.source_import_batch_id,
            "created_at": _iso(student.created_at),
            "updated_at": _iso(student.updated_at),
        },
        "application_record": _serialize_application(application),
        "report_summary": _serialize_summary(summary),
        "active_reports": [_serialize_report(report) for report in reports],
    }


def _serialize_application(record: ApplicationRecord | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        "id": record.pk,
        "applied_at": _iso(record.applied_at),
        "source_import_batch_id": record.source_import_batch_id,
        "created_at": _iso(record.created_at),
        "updated_at": _iso(record.updated_at),
    }


def _serialize_summary(summary: IdeologicalReportSummary | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    return {
        "id": summary.pk,
        "reported_total_count": summary.reported_total_count,
        "calculated_date_count": summary.calculated_date_count,
        "source_import_batch_id": summary.source_import_batch_id,
        "created_at": _iso(summary.created_at),
        "updated_at": _iso(summary.updated_at),
    }


def _serialize_report(report: IdeologicalReport) -> dict[str, Any]:
    return {
        "id": report.pk,
        "sequence_number": report.sequence_number,
        "submitted_at": _iso(report.submitted_at),
        "source_column_name": report.source_column_name,
        "import_batch_id": report.import_batch_id,
        "is_active": report.is_active,
        "created_at": _iso(report.created_at),
    }


def _write_json_evidence(
    batch: ImportBatch,
    document: dict[str, Any],
    *,
    filename: str,
    hash_filename: str,
) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    document_path = artifact_path(batch.pk, filename)
    digest_path = artifact_path(batch.pk, hash_filename)
    try:
        _atomic_write(document_path, payload)
        _atomic_write(digest_path, digest.encode("ascii"))
    except Exception:
        document_path.unlink(missing_ok=True)
        digest_path.unlink(missing_ok=True)
        raise
    return digest


def _create_consistent_database_backup(batch: ImportBatch) -> Path:
    destination = artifact_path(batch.pk, PRE_IMPORT_DATABASE_FILENAME)
    temporary = artifact_path(
        batch.pk, f".{PRE_IMPORT_DATABASE_FILENAME}.{uuid.uuid4().hex}.tmp"
    )
    connection.ensure_connection()
    source = connection.connection
    if source is None:
        raise RuntimeError("SQLite数据库连接不可用。")

    try:
        if connection.in_atomic_block and str(connection.settings_dict["NAME"]).startswith("file:"):
            payload = source.serialize()
            _atomic_write(temporary, payload)
        else:
            backup = sqlite3.connect(temporary)
            try:
                source.backup(backup)
            finally:
                backup.close()
        _verify_sqlite_backup(temporary)
        os.replace(temporary, destination)
        return destination
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _verify_sqlite_backup(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("SQLite备份为空。")
    database = sqlite3.connect(path)
    try:
        result = database.execute("PRAGMA integrity_check").fetchone()
    finally:
        database.close()
    if result != ("ok",):
        raise RuntimeError("SQLite备份完整性检查失败。")


def verify_pre_import_database_backup(batch: ImportBatch) -> Path:
    """供PR3复用：校验备份完整性及其与previewed批次的绑定。"""
    path = artifact_path(batch.pk, PRE_IMPORT_DATABASE_FILENAME)
    _verify_sqlite_backup(path)
    database = sqlite3.connect(path)
    try:
        row = database.execute(
            "SELECT status, file_hash FROM imports_importbatch WHERE id = ?", (batch.pk,)
        ).fetchone()
    finally:
        database.close()
    if row != (ImportStatus.PREVIEWED, batch.file_hash):
        raise RuntimeError("SQLite备份与导入批次不匹配。")
    return path


def _apply_candidates(batch: ImportBatch, rows: list[dict[str, Any]]) -> None:
    branches = {
        branch.code: branch
        for branch in PartyBranch.objects.filter(
            code__in={row["branch_code"] for row in rows}, is_active=True
        )
    }
    created_students = 0
    updated_students = 0
    created_reports = 0
    updated_applications = 0

    for row in rows:
        student = Student.objects.filter(student_number=row["student_number"]).first()
        if student is None:
            student = Student.objects.create(
                name=row["name"],
                student_number=row["student_number"],
                branch=branches[row["branch_code"]],
                development_stage=row["development_stage"],
                position=row["position"],
                source_import_batch=batch,
            )
            created_students += 1
        else:
            student.name = row["name"]
            student.branch = branches[row["branch_code"]]
            student.development_stage = row["development_stage"]
            if row["position"]:
                student.position = row["position"]
            student.source_import_batch = batch
            student.save()
            updated_students += 1

        applied_at = _parse_optional_date(row["applied_at"])
        if applied_at is not None:
            application, _ = ApplicationRecord.objects.get_or_create(student=student)
            application.applied_at = applied_at
            application.source_import_batch = batch
            application.save()
            updated_applications += 1

        summary, _ = IdeologicalReportSummary.objects.get_or_create(student=student)
        if row["reported_total_count"] is not None:
            summary.reported_total_count = row["reported_total_count"]
        summary.calculated_date_count = row["calculated_date_count"]
        summary.source_import_batch = batch
        summary.save()

        student.ideological_reports.filter(is_active=True).delete()
        reports = [
            IdeologicalReport(
                student=student,
                sequence_number=item["sequence_number"],
                submitted_at=parse_date(item["submitted_at"]),
                source_column_name=item["source_column_name"],
                import_batch=batch,
                is_active=True,
            )
            for item in row["report_items"]
        ]
        IdeologicalReport.objects.bulk_create(reports)
        created_reports += len(reports)

    batch.created_students = created_students
    batch.updated_students = updated_students
    batch.created_reports = created_reports
    batch.updated_applications = updated_applications


def _mark_batch_failed(batch_id: int, failure_message: str) -> bool:
    try:
        updated = ImportBatch.objects.filter(
            pk=batch_id, status=ImportStatus.PREVIEWED
        ).update(
            status=ImportStatus.FAILED,
            failure_message=failure_message,
        )
        return updated == 1
    except Exception:
        logger.exception("无法保存导入失败状态", extra={"batch_id": batch_id})
        return False


@contextmanager
def _confirmation_lock(timeout: float = CONFIRM_LOCK_TIMEOUT_SECONDS) -> Iterator[None]:
    root = (Path(settings.MEDIA_ROOT) / "imports").resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".confirm_import.lock"
    deadline = time.monotonic() + timeout
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR)
    if os.path.getsize(lock_path) == 0:
        os.write(descriptor, b"0")
        os.fsync(descriptor)
    acquired = False
    while not acquired:
        try:
            _try_lock_descriptor(descriptor)
            acquired = True
        except (BlockingIOError, OSError):
            if time.monotonic() >= deadline:
                os.close(descriptor)
                raise TimeoutError("确认导入锁等待超时。")
            time.sleep(0.05)
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.fsync(descriptor)
        yield
    finally:
        _unlock_descriptor(descriptor)
        os.close(descriptor)


def _try_lock_descriptor(descriptor: int) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_descriptor(descriptor: int) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_UN)


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as destination:
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _parse_optional_date(value: str | None) -> date | None:
    return parse_date(value) if value is not None else None


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
