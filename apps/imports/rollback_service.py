from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.audit.services import record_operation_log
from apps.imports.import_service import _confirmation_lock, verify_pre_import_database_backup
from apps.imports.models import ImportBatch, ImportStatus
from apps.imports.snapshots import load_preview_snapshot, load_rollback_snapshot
from apps.imports.storage import ImportEvidenceError
from apps.materials.models import ApplicationRecord, IdeologicalReport, IdeologicalReportSummary
from apps.students.models import Student, StudentStatus


@dataclass(frozen=True)
class RollbackConflict:
    code: str
    message: str
    student_number: str = ""


@dataclass(frozen=True)
class RollbackImpact:
    existing_students_to_restore: int = 0
    new_students_to_delete: int = 0
    applications_to_restore: int = 0
    summaries_to_restore: int = 0
    reports_to_replace: int = 0


@dataclass(frozen=True)
class RollbackAssessment:
    batch_id: int
    eligible: bool
    conflicts: tuple[RollbackConflict, ...]
    impact: RollbackImpact


class RollbackBatchNotFound(Exception):
    """指定导入批次不存在。"""


class RollbackRejected(Exception):
    """回滚资格、证据或当前数据存在冲突。"""

    def __init__(self, assessment: RollbackAssessment):
        self.assessment = assessment
        super().__init__("当前批次不满足安全回滚条件。")


class RollbackFailed(Exception):
    """回滚事务执行失败，所有变更已撤销。"""


def get_rollback_candidate() -> ImportBatch | None:
    """返回当前最新成功且尚未回滚的批次。"""
    return (
        ImportBatch.objects.filter(status=ImportStatus.SUCCESS)
        .order_by("-imported_at", "-pk")
        .first()
    )


def assess_rollback(batch_id: int) -> RollbackAssessment:
    """只读评估回滚资格、影响范围及所有可发现冲突。"""
    try:
        batch = ImportBatch.objects.get(pk=batch_id)
    except ImportBatch.DoesNotExist as exc:
        raise RollbackBatchNotFound(str(batch_id)) from exc

    conflicts: list[RollbackConflict] = []
    _validate_batch_state(batch, conflicts)
    preview: dict[str, Any] | None = None
    rollback: dict[str, Any] | None = None
    try:
        preview = load_preview_snapshot(batch)
        rollback = load_rollback_snapshot(batch)
        verify_pre_import_database_backup(batch)
    except ImportEvidenceError as exc:
        conflicts.append(RollbackConflict("ROLLBACK_EVIDENCE_INVALID", str(exc)))
    except Exception:
        conflicts.append(
            RollbackConflict("PRE_IMPORT_BACKUP_INVALID", "导入前SQLite备份校验失败。")
        )

    impact = RollbackImpact()
    if preview is not None and rollback is not None:
        impact = _calculate_impact(rollback)
        conflicts.extend(_detect_business_conflicts(batch, preview, rollback))
    return RollbackAssessment(
        batch_id=batch.pk,
        eligible=not conflicts,
        conflicts=tuple(conflicts),
        impact=impact,
    )


def rollback_import(request: HttpRequest, batch_id: int) -> ImportBatch:
    """在项目级串行锁和单一事务中完整恢复最近成功批次。"""
    with _confirmation_lock():
        assessment = assess_rollback(batch_id)
        if not assessment.eligible:
            raise RollbackRejected(assessment)
        try:
            with transaction.atomic():
                batch = ImportBatch.objects.select_for_update().get(pk=batch_id)
                assessment = assess_rollback(batch_id)
                if not assessment.eligible:
                    raise RollbackRejected(assessment)
                rollback = load_rollback_snapshot(batch)
                _restore_students(batch, rollback)
                batch.status = ImportStatus.ROLLED_BACK
                batch.rolled_back_at = timezone.now()
                batch.rolled_back_by = request.user
                batch.save(update_fields=["status", "rolled_back_at", "rolled_back_by"])
                record_operation_log(
                    request,
                    action="rollback_import",
                    target_type="ImportBatch",
                    target_id=str(batch.pk),
                    description=f"回滚最近成功Excel导入：{batch.original_filename}",
                )
            return batch
        except RollbackRejected:
            raise
        except Exception as exc:
            raise RollbackFailed("回滚失败，业务数据已完整撤销。") from exc


def _restore_students(batch: ImportBatch, rollback: dict[str, Any]) -> None:
    for record in rollback["students"]:
        number = record["student_number"]
        student = Student.objects.select_for_update().get(student_number=number)
        if not record["student_existed_before"]:
            student.delete()
            continue
        _restore_student(student, record["student"])
        _restore_application(student, record["application_record"])
        _restore_summary(student, record["report_summary"])
        _restore_reports(student, record["active_reports"])


def _restore_student(student: Student, snapshot: dict[str, Any]) -> None:
    student.name = snapshot["name"]
    student.branch_id = snapshot["branch_id"]
    student.development_stage = snapshot["development_stage"]
    student.position = snapshot["position"]
    student.status = snapshot["status"]
    student.source_import_batch_id = snapshot["source_import_batch_id"]
    student.save()
    Student.objects.filter(pk=student.pk).update(
        created_at=_parse_datetime(snapshot["created_at"]),
        updated_at=_parse_datetime(snapshot["updated_at"]),
    )


def _restore_application(student: Student, snapshot: dict[str, Any] | None) -> None:
    current = ApplicationRecord.objects.filter(student=student)
    if snapshot is None:
        current.delete()
        return
    record, _ = ApplicationRecord.objects.update_or_create(
        student=student,
        defaults={
            "applied_at": parse_date(snapshot["applied_at"]) if snapshot["applied_at"] else None,
            "source_import_batch_id": snapshot["source_import_batch_id"],
        },
    )
    ApplicationRecord.objects.filter(pk=record.pk).update(
        created_at=_parse_datetime(snapshot["created_at"]),
        updated_at=_parse_datetime(snapshot["updated_at"]),
    )


def _restore_summary(student: Student, snapshot: dict[str, Any] | None) -> None:
    current = IdeologicalReportSummary.objects.filter(student=student)
    if snapshot is None:
        current.delete()
        return
    summary, _ = IdeologicalReportSummary.objects.update_or_create(
        student=student,
        defaults={
            "reported_total_count": snapshot["reported_total_count"],
            "calculated_date_count": snapshot["calculated_date_count"],
            "source_import_batch_id": snapshot["source_import_batch_id"],
        },
    )
    IdeologicalReportSummary.objects.filter(pk=summary.pk).update(
        created_at=_parse_datetime(snapshot["created_at"]),
        updated_at=_parse_datetime(snapshot["updated_at"]),
    )


def _restore_reports(student: Student, snapshots: list[dict[str, Any]]) -> None:
    student.ideological_reports.filter(is_active=True).delete()
    for snapshot in snapshots:
        report = IdeologicalReport.objects.create(
            id=snapshot["id"],
            student=student,
            sequence_number=snapshot["sequence_number"],
            submitted_at=parse_date(snapshot["submitted_at"]),
            source_column_name=snapshot["source_column_name"],
            import_batch_id=snapshot["import_batch_id"],
            is_active=True,
        )
        IdeologicalReport.objects.filter(pk=report.pk).update(
            created_at=_parse_datetime(snapshot["created_at"])
        )


def _parse_datetime(value: str) -> datetime:
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValueError("回滚时间字段无效。")
    return parsed


def _validate_batch_state(batch: ImportBatch, conflicts: list[RollbackConflict]) -> None:
    if batch.status != ImportStatus.SUCCESS:
        conflicts.append(
            RollbackConflict("BATCH_STATUS_NOT_SUCCESS", "只有成功批次可以回滚。")
        )
        return
    latest = get_rollback_candidate()
    if latest is None or latest.pk != batch.pk:
        conflicts.append(
            RollbackConflict("BATCH_NOT_LATEST_SUCCESS", "只能回滚最近一次成功批次。")
        )


def _calculate_impact(rollback: dict[str, Any]) -> RollbackImpact:
    records = rollback["students"]
    existing = [record for record in records if record["student_existed_before"]]
    return RollbackImpact(
        existing_students_to_restore=len(existing),
        new_students_to_delete=len(records) - len(existing),
        applications_to_restore=sum(
            record["application_record"] is not None for record in existing
        ),
        summaries_to_restore=sum(record["report_summary"] is not None for record in existing),
        reports_to_replace=sum(len(record["active_reports"]) for record in existing),
    )


def _detect_business_conflicts(
    batch: ImportBatch,
    preview: dict[str, Any],
    rollback: dict[str, Any],
) -> list[RollbackConflict]:
    conflicts: list[RollbackConflict] = []
    before_by_number = {
        record["student_number"]: record for record in rollback["students"]
    }
    rows_by_number = {row["student_number"]: row for row in preview["valid_rows"]}
    if set(before_by_number) != set(rows_by_number):
        return [RollbackConflict("SNAPSHOT_CANDIDATE_MISMATCH", "回滚快照与确认候选不一致。")]

    students = {
        student.student_number: student
        for student in Student.objects.filter(student_number__in=rows_by_number).select_related(
            "branch"
        )
    }
    for number, row in rows_by_number.items():
        before = before_by_number[number]
        student = students.get(number)
        if student is None:
            conflicts.append(
                RollbackConflict("CURRENT_STUDENT_MISSING", "当前学生记录不存在。", number)
            )
            continue
        conflicts.extend(_compare_student(batch, student, row, before))
        conflicts.extend(_compare_application(batch, student, row, before))
        conflicts.extend(_compare_summary(batch, student, row, before))
        conflicts.extend(_compare_reports(batch, student, row))
    return conflicts


def _compare_student(
    batch: ImportBatch, student: Student, row: dict[str, Any], before: dict[str, Any]
) -> list[RollbackConflict]:
    if before["student_existed_before"]:
        old = before["student"]
        expected_position = row["position"] or old["position"]
        expected_status = old["status"]
    else:
        expected_position = row["position"]
        expected_status = StudentStatus.ACTIVE
    expected = (
        row["name"],
        row["branch_code"],
        row["development_stage"],
        expected_position,
        expected_status,
        batch.pk,
    )
    actual = (
        student.name,
        student.branch.code,
        student.development_stage,
        student.position,
        student.status,
        student.source_import_batch_id,
    )
    if actual != expected or (
        batch.imported_at is not None and student.updated_at > batch.imported_at
    ):
        return [
            RollbackConflict(
                "STUDENT_MODIFIED_AFTER_IMPORT", "学生主数据在导入后发生修改。", student.student_number
            )
        ]
    return []


def _compare_application(
    batch: ImportBatch, student: Student, row: dict[str, Any], before: dict[str, Any]
) -> list[RollbackConflict]:
    current = ApplicationRecord.objects.filter(student=student).first()
    if row["applied_at"] is not None:
        expected = (row["applied_at"], batch.pk)
    else:
        old = before["application_record"]
        expected = None if old is None else (old["applied_at"], old["source_import_batch_id"])
    actual = None if current is None else (
        current.applied_at.isoformat() if current.applied_at else None,
        current.source_import_batch_id,
    )
    if actual != expected or (
        current is not None
        and batch.imported_at is not None
        and current.updated_at > batch.imported_at
    ):
        return [RollbackConflict("APPLICATION_MODIFIED_AFTER_IMPORT", "申请记录在导入后发生修改。", student.student_number)]
    return []


def _compare_summary(
    batch: ImportBatch, student: Student, row: dict[str, Any], before: dict[str, Any]
) -> list[RollbackConflict]:
    current = IdeologicalReportSummary.objects.filter(student=student).first()
    old = before["report_summary"]
    expected_reported = row["reported_total_count"]
    if expected_reported is None and old is not None:
        expected_reported = old["reported_total_count"]
    expected = (expected_reported, row["calculated_date_count"], batch.pk)
    actual = None if current is None else (
        current.reported_total_count,
        current.calculated_date_count,
        current.source_import_batch_id,
    )
    if actual != expected or (
        current is not None
        and batch.imported_at is not None
        and current.updated_at > batch.imported_at
    ):
        return [RollbackConflict("SUMMARY_MODIFIED_AFTER_IMPORT", "思想汇报汇总在导入后发生修改。", student.student_number)]
    return []


def _compare_reports(
    batch: ImportBatch, student: Student, row: dict[str, Any]
) -> list[RollbackConflict]:
    expected = sorted(
        (
            item["sequence_number"],
            item["submitted_at"],
            item["source_column_name"],
            batch.pk,
        )
        for item in row["report_items"]
    )
    actual = sorted(
        (
            report.sequence_number,
            report.submitted_at.isoformat(),
            report.source_column_name,
            report.import_batch_id,
        )
        for report in student.ideological_reports.filter(is_active=True)
    )
    has_later_record = batch.imported_at is not None and any(
        report.created_at > batch.imported_at
        for report in student.ideological_reports.filter(is_active=True)
    )
    if actual != expected or has_later_record:
        return [RollbackConflict("REPORTS_MODIFIED_AFTER_IMPORT", "有效思想汇报在导入后发生修改。", student.student_number)]
    return []
