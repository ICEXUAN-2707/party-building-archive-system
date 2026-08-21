from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.imports.datatypes import ParseResult, ParseWarning, ParsedStudentRow
from apps.imports.models import ImportBatch
from apps.imports.storage import (
    ImportEvidenceIntegrityError,
    ImportEvidenceNotFound,
    artifact_path,
    verified_original_path,
)


PREVIEW_SCHEMA_VERSION = 1
PREVIEW_FILENAME = "preview.json"
PREVIEW_HASH_FILENAME = "preview.sha256"
ROLLBACK_SCHEMA_VERSION = 1
ROLLBACK_FILENAME = "rollback_snapshot.json"
ROLLBACK_HASH_FILENAME = "rollback_snapshot.sha256"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_STATISTIC_FIELDS = (
    "total_sheets",
    "success_sheets",
    "failed_sheets",
    "total_rows",
    "success_rows",
    "skipped_rows",
    "warning_rows",
)


def build_preview_snapshot(batch: ImportBatch, result: ParseResult) -> dict[str, Any]:
    valid_rows = [_serialize_student_row(row) for row in result.valid_rows]
    duplicate_numbers = _duplicate_student_numbers(result.valid_rows)
    return {
        "schema_version": PREVIEW_SCHEMA_VERSION,
        "import_batch_id": batch.pk,
        "file_sha256": batch.file_hash,
        "created_at": timezone.now().isoformat(),
        "statistics": {
            field: getattr(result, field)
            for field in _STATISTIC_FIELDS
        },
        "sheet_results": [
            {
                "sheet_name": sheet.sheet_name,
                "branch_code": sheet.branch_code,
                "branch_name": sheet.branch_name,
                "status": sheet.status,
                "total_rows": sheet.total_rows,
                "valid_row_count": sheet.valid_row_count,
                "error_count": sheet.error_count,
                "warning_count": sheet.warning_count,
            }
            for sheet in result.sheet_results
        ],
        "valid_rows": valid_rows,
        "conflicts": [
            {
                "code": "DUPLICATE_STUDENT_NUMBER",
                "student_number": student_number,
                "message": f"同一工作簿中学号{student_number}出现多次，后续确认必须拒绝。",
            }
            for student_number in duplicate_numbers
        ],
        "can_confirm": bool(valid_rows) and not duplicate_numbers,
    }


def write_preview_snapshot(batch: ImportBatch, snapshot: dict[str, Any]) -> str:
    validate_preview_snapshot(snapshot, batch=batch, verify_original=True)
    payload = json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()

    preview_path = artifact_path(batch.pk, PREVIEW_FILENAME)
    hash_path = artifact_path(batch.pk, PREVIEW_HASH_FILENAME)
    preview_temp = artifact_path(batch.pk, f".{PREVIEW_FILENAME}.{uuid.uuid4().hex}.tmp")
    hash_temp = artifact_path(batch.pk, f".{PREVIEW_HASH_FILENAME}.{uuid.uuid4().hex}.tmp")

    try:
        _atomic_stage(preview_temp, payload)
        _atomic_stage(hash_temp, digest.encode("ascii"))
        os.replace(preview_temp, preview_path)
        os.replace(hash_temp, hash_path)
    except Exception:
        preview_temp.unlink(missing_ok=True)
        hash_temp.unlink(missing_ok=True)
        raise
    return digest


def load_preview_snapshot(batch: ImportBatch) -> dict[str, Any]:
    verified_original_path(batch)
    preview_path = artifact_path(batch.pk, PREVIEW_FILENAME)
    hash_path = artifact_path(batch.pk, PREVIEW_HASH_FILENAME)
    if not preview_path.is_file() or not hash_path.is_file():
        raise ImportEvidenceNotFound("预览快照不存在。")

    payload = preview_path.read_bytes()
    expected_hash = hash_path.read_text(encoding="ascii").strip()
    if not _SHA256_PATTERN.fullmatch(expected_hash):
        raise ImportEvidenceIntegrityError("预览快照哈希格式无效。")
    if hashlib.sha256(payload).hexdigest() != expected_hash:
        raise ImportEvidenceIntegrityError("预览快照完整性校验失败。")

    try:
        snapshot = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ImportEvidenceIntegrityError("预览快照不是有效JSON。") from exc
    validate_preview_snapshot(snapshot, batch=batch, verify_original=False)
    return snapshot


def load_rollback_snapshot(batch: ImportBatch) -> dict[str, Any]:
    """读取并完整校验供PR3消费的导入前业务快照。"""
    snapshot_path = artifact_path(batch.pk, ROLLBACK_FILENAME)
    hash_path = artifact_path(batch.pk, ROLLBACK_HASH_FILENAME)
    if not snapshot_path.is_file() or not hash_path.is_file():
        raise ImportEvidenceNotFound("回滚快照不存在。")
    payload = snapshot_path.read_bytes()
    expected_hash = hash_path.read_text(encoding="ascii").strip()
    if not _SHA256_PATTERN.fullmatch(expected_hash):
        raise ImportEvidenceIntegrityError("回滚快照哈希格式无效。")
    if hashlib.sha256(payload).hexdigest() != expected_hash:
        raise ImportEvidenceIntegrityError("回滚快照完整性校验失败。")
    try:
        snapshot = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ImportEvidenceIntegrityError("回滚快照不是有效JSON。") from exc
    validate_rollback_snapshot(snapshot, batch=batch)
    return snapshot


def validate_rollback_snapshot(snapshot: object, *, batch: ImportBatch) -> None:
    if not isinstance(snapshot, dict):
        raise ImportEvidenceIntegrityError("回滚快照顶层必须是对象。")
    if snapshot.get("schema_version") != ROLLBACK_SCHEMA_VERSION:
        raise ImportEvidenceIntegrityError("回滚快照schema版本无效。")
    if snapshot.get("import_batch_id") != batch.pk:
        raise ImportEvidenceIntegrityError("回滚快照与批次不匹配。")
    if parse_datetime(snapshot.get("created_at", "")) is None:
        raise ImportEvidenceIntegrityError("回滚快照创建时间无效。")
    preview_hash_path = artifact_path(batch.pk, PREVIEW_HASH_FILENAME)
    if not preview_hash_path.is_file():
        raise ImportEvidenceNotFound("预览快照哈希不存在。")
    preview_hash = preview_hash_path.read_text(encoding="ascii").strip()
    if not _SHA256_PATTERN.fullmatch(preview_hash):
        raise ImportEvidenceIntegrityError("预览快照哈希格式无效。")
    if snapshot.get("preview_sha256") != preview_hash:
        raise ImportEvidenceIntegrityError("回滚快照与预览证据不匹配。")
    students = snapshot.get("students")
    if not isinstance(students, list):
        raise ImportEvidenceIntegrityError("回滚学生快照必须是数组。")
    if snapshot.get("record_count") != len(students):
        raise ImportEvidenceIntegrityError("回滚快照记录数无效。")
    numbers: set[str] = set()
    for index, record in enumerate(students):
        _validate_rollback_student(record, index)
        number = record["student_number"]
        if number in numbers:
            raise ImportEvidenceIntegrityError("回滚快照存在重复学号。")
        numbers.add(number)


def _validate_rollback_student(record: object, index: int) -> None:
    if not isinstance(record, dict):
        raise ImportEvidenceIntegrityError(f"students[{index}]必须是对象。")
    number = record.get("student_number")
    existed = record.get("student_existed_before")
    if not isinstance(number, str) or not number:
        raise ImportEvidenceIntegrityError(f"students[{index}].student_number无效。")
    if not isinstance(existed, bool):
        raise ImportEvidenceIntegrityError(f"students[{index}].student_existed_before无效。")
    student = record.get("student")
    application = record.get("application_record")
    summary = record.get("report_summary")
    reports = record.get("active_reports")
    if not isinstance(reports, list):
        raise ImportEvidenceIntegrityError(f"students[{index}].active_reports无效。")
    if not existed:
        if student is not None or application is not None or summary is not None or reports:
            raise ImportEvidenceIntegrityError("导入前不存在的学生不得包含旧业务状态。")
        return
    if not isinstance(student, dict) or student.get("student_number") != number:
        raise ImportEvidenceIntegrityError("已有学生快照与学号不匹配。")
    for field in ("id", "branch_id"):
        _require_positive_integer(student.get(field), f"students[{index}].student.{field}")
    for field in ("name", "development_stage", "position", "status"):
        if not isinstance(student.get(field), str):
            raise ImportEvidenceIntegrityError(f"students[{index}].student.{field}无效。")
    for item in (application, summary):
        if item is not None and not isinstance(item, dict):
            raise ImportEvidenceIntegrityError("材料快照必须是对象或null。")
    sequences: set[int] = set()
    for report in reports:
        if not isinstance(report, dict) or report.get("is_active") is not True:
            raise ImportEvidenceIntegrityError("回滚思想汇报必须是有效记录。")
        sequence = report.get("sequence_number")
        _require_positive_integer(sequence, "active_reports.sequence_number")
        if sequence in sequences:
            raise ImportEvidenceIntegrityError("回滚思想汇报次数重复。")
        sequences.add(sequence)
        if not isinstance(report.get("submitted_at"), str) or parse_date(report["submitted_at"]) is None:
            raise ImportEvidenceIntegrityError("回滚思想汇报日期无效。")


def validate_preview_snapshot(
    snapshot: object,
    *,
    batch: ImportBatch,
    verify_original: bool = True,
) -> None:
    if verify_original:
        verified_original_path(batch)
    if not isinstance(snapshot, dict):
        raise ImportEvidenceIntegrityError("预览快照顶层必须是对象。")
    if snapshot.get("schema_version") != PREVIEW_SCHEMA_VERSION:
        raise ImportEvidenceIntegrityError("预览快照schema版本不受支持。")
    if snapshot.get("import_batch_id") != batch.pk:
        raise ImportEvidenceIntegrityError("预览快照与导入批次不匹配。")
    if snapshot.get("file_sha256") != batch.file_hash:
        raise ImportEvidenceIntegrityError("预览快照与原始Excel哈希不匹配。")
    if parse_datetime(snapshot.get("created_at", "")) is None:
        raise ImportEvidenceIntegrityError("预览快照创建时间无效。")

    statistics = snapshot.get("statistics")
    if not isinstance(statistics, dict):
        raise ImportEvidenceIntegrityError("预览统计结构无效。")
    for field in _STATISTIC_FIELDS:
        _require_non_negative_integer(statistics.get(field), f"statistics.{field}")

    sheet_results = snapshot.get("sheet_results")
    if not isinstance(sheet_results, list):
        raise ImportEvidenceIntegrityError("工作表预览结构无效。")
    for index, sheet in enumerate(sheet_results):
        _validate_sheet_result(sheet, index)

    valid_rows = snapshot.get("valid_rows")
    if not isinstance(valid_rows, list):
        raise ImportEvidenceIntegrityError("有效行预览结构无效。")
    for index, row in enumerate(valid_rows):
        _validate_student_row(row, index)

    if statistics["total_sheets"] != len(sheet_results):
        raise ImportEvidenceIntegrityError("工作表总数与预览明细不一致。")
    if statistics["success_sheets"] + statistics["failed_sheets"] != statistics["total_sheets"]:
        raise ImportEvidenceIntegrityError("成功/失败工作表统计不一致。")
    if sum(sheet["valid_row_count"] for sheet in sheet_results) != statistics["success_rows"]:
        raise ImportEvidenceIntegrityError("有效行统计与工作表明细不一致。")
    if statistics["success_rows"] != len(valid_rows):
        raise ImportEvidenceIntegrityError("有效行统计与预览候选数不一致。")
    if sum(sheet["total_rows"] for sheet in sheet_results) != statistics["total_rows"]:
        raise ImportEvidenceIntegrityError("总行数与工作表明细不一致。")

    conflicts = snapshot.get("conflicts", [])
    if not isinstance(conflicts, list):
        raise ImportEvidenceIntegrityError("预览冲突结构无效。")
    conflict_numbers: set[str] = set()
    for index, conflict in enumerate(conflicts):
        if not isinstance(conflict, dict):
            raise ImportEvidenceIntegrityError(f"conflicts[{index}]必须是对象。")
        if conflict.get("code") != "DUPLICATE_STUDENT_NUMBER":
            raise ImportEvidenceIntegrityError(f"conflicts[{index}].code无效。")
        if not isinstance(conflict.get("student_number"), str) or not conflict["student_number"]:
            raise ImportEvidenceIntegrityError(f"conflicts[{index}].student_number无效。")
        if not isinstance(conflict.get("message"), str) or not conflict["message"]:
            raise ImportEvidenceIntegrityError(f"conflicts[{index}].message无效。")
        conflict_numbers.add(conflict["student_number"])
    actual_duplicate_numbers = _duplicate_numbers_from_snapshot(valid_rows)
    if conflict_numbers != actual_duplicate_numbers:
        raise ImportEvidenceIntegrityError("重复学号冲突与有效行内容不一致。")
    if not isinstance(snapshot.get("can_confirm"), bool):
        raise ImportEvidenceIntegrityError("预览确认标志无效。")
    expected_can_confirm = bool(valid_rows) and not conflicts
    if snapshot["can_confirm"] != expected_can_confirm:
        raise ImportEvidenceIntegrityError("预览确认标志与候选数据不一致。")


def _serialize_student_row(row: ParsedStudentRow) -> dict[str, Any]:
    return {
        "sheet_name": row.sheet_name,
        "excel_row_number": row.excel_row_number,
        "branch_code": row.branch_code,
        "branch_name": row.branch_name,
        "name": row.name,
        "student_number": row.student_number,
        "development_stage": row.development_stage,
        "position": row.position,
        "applied_at": _date_to_iso(row.applied_at),
        "reported_total_count": row.reported_total_count,
        "calculated_date_count": row.calculated_date_count,
        "report_items": [
            {
                "sequence_number": item.sequence_number,
                "submitted_at": item.submitted_at.isoformat(),
                "source_column_name": item.source_column_name,
            }
            for item in row.report_items
        ],
        "warnings": [_serialize_warning(warning) for warning in row.warnings],
    }


def _serialize_warning(warning: ParseWarning) -> dict[str, Any]:
    return {
        "code": warning.code,
        "message": warning.message,
        "sheet_name": warning.sheet_name,
        "excel_row_number": warning.excel_row_number,
        "student_name": warning.student_name,
        "student_number": warning.student_number,
        "field_name": warning.field_name,
        "source_value": warning.source_value,
        "parsed_value": warning.parsed_value,
    }


def _duplicate_student_numbers(rows: list[ParsedStudentRow]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        if row.student_number in seen:
            duplicates.add(row.student_number)
        seen.add(row.student_number)
    return sorted(duplicates)


def _validate_sheet_result(sheet: object, index: int) -> None:
    if not isinstance(sheet, dict):
        raise ImportEvidenceIntegrityError(f"sheet_results[{index}]必须是对象。")
    for field in ("sheet_name", "status"):
        if not isinstance(sheet.get(field), str) or not sheet[field]:
            raise ImportEvidenceIntegrityError(f"sheet_results[{index}].{field}无效。")
    for field in ("branch_code", "branch_name"):
        if sheet.get(field) is not None and not isinstance(sheet[field], str):
            raise ImportEvidenceIntegrityError(f"sheet_results[{index}].{field}无效。")
    for field in ("total_rows", "valid_row_count", "error_count", "warning_count"):
        _require_non_negative_integer(sheet.get(field), f"sheet_results[{index}].{field}")


def _validate_student_row(row: object, index: int) -> None:
    if not isinstance(row, dict):
        raise ImportEvidenceIntegrityError(f"valid_rows[{index}]必须是对象。")
    for field in (
        "sheet_name",
        "branch_code",
        "branch_name",
        "name",
        "student_number",
        "development_stage",
        "position",
    ):
        if not isinstance(row.get(field), str):
            raise ImportEvidenceIntegrityError(f"valid_rows[{index}].{field}类型无效。")
    for required in ("sheet_name", "branch_code", "name", "student_number", "development_stage"):
        if not row[required]:
            raise ImportEvidenceIntegrityError(f"valid_rows[{index}].{required}不能为空。")
    _require_positive_integer(row.get("excel_row_number"), f"valid_rows[{index}].excel_row_number")
    _require_non_negative_integer(
        row.get("calculated_date_count"),
        f"valid_rows[{index}].calculated_date_count",
    )
    reported_total = row.get("reported_total_count")
    if reported_total is not None:
        _require_non_negative_integer(reported_total, f"valid_rows[{index}].reported_total_count")
    applied_at = row.get("applied_at")
    if applied_at is not None and (not isinstance(applied_at, str) or parse_date(applied_at) is None):
        raise ImportEvidenceIntegrityError(f"valid_rows[{index}].applied_at无效。")

    report_items = row.get("report_items")
    if not isinstance(report_items, list):
        raise ImportEvidenceIntegrityError(f"valid_rows[{index}].report_items无效。")
    for report_index, item in enumerate(report_items):
        if not isinstance(item, dict):
            raise ImportEvidenceIntegrityError("思想汇报预览项必须是对象。")
        _require_positive_integer(
            item.get("sequence_number"),
            f"valid_rows[{index}].report_items[{report_index}].sequence_number",
        )
        submitted_at = item.get("submitted_at")
        if not isinstance(submitted_at, str) or parse_date(submitted_at) is None:
            raise ImportEvidenceIntegrityError("思想汇报提交日期无效。")
        if not isinstance(item.get("source_column_name"), str):
            raise ImportEvidenceIntegrityError("思想汇报来源列无效。")
    warnings = row.get("warnings")
    if not isinstance(warnings, list):
        raise ImportEvidenceIntegrityError(f"valid_rows[{index}].warnings无效。")
    for warning_index, warning in enumerate(warnings):
        if not isinstance(warning, dict):
            raise ImportEvidenceIntegrityError("有效行警告项必须是对象。")
        for field in (
            "code",
            "message",
            "sheet_name",
            "student_name",
            "student_number",
            "field_name",
            "source_value",
            "parsed_value",
        ):
            if not isinstance(warning.get(field), str):
                raise ImportEvidenceIntegrityError(
                    f"valid_rows[{index}].warnings[{warning_index}].{field}类型无效。"
                )
        warning_row = warning.get("excel_row_number")
        if warning_row is not None:
            _require_positive_integer(
                warning_row,
                f"valid_rows[{index}].warnings[{warning_index}].excel_row_number",
            )


def _require_non_negative_integer(value: object, field: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ImportEvidenceIntegrityError(f"{field}必须是非负整数。")


def _require_positive_integer(value: object, field: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ImportEvidenceIntegrityError(f"{field}必须是正整数。")


def _date_to_iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _duplicate_numbers_from_snapshot(rows: list[dict[str, Any]]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        student_number = row["student_number"]
        if student_number in seen:
            duplicates.add(student_number)
        seen.add(student_number)
    return duplicates


def _atomic_stage(path: Path, payload: bytes) -> None:
    with path.open("xb") as destination:
        destination.write(payload)
        destination.flush()
        os.fsync(destination.fileno())
