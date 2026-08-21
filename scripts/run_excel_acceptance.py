from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_acceptance_excel import AcceptanceDataset, generate_acceptance_dataset


def _configure_django(database_path: Path) -> None:
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    os.environ["DJANGO_SQLITE_PATH"] = str(database_path)
    os.environ.setdefault("DJANGO_SECRET_KEY", "synthetic-acceptance-only")
    import django

    django.setup()


def run_acceptance(output_directory: Path, *, student_count: int, seed: int) -> Path:
    if output_directory.exists() and any(output_directory.iterdir()):
        raise RuntimeError("验收输出目录必须不存在或为空，避免覆盖既有证据。")
    output_directory.mkdir(parents=True, exist_ok=True)
    database_path = output_directory / "acceptance.sqlite3"
    media_root = output_directory / "media"
    media_root.mkdir()
    dataset_directory = output_directory / "dataset"
    dataset = generate_acceptance_dataset(
        dataset_directory,
        student_count=student_count,
        seed=seed,
    )
    _configure_django(database_path)

    from django.conf import settings
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.core.management import call_command
    from django.db import connections
    from django.test import Client
    from django.urls import reverse

    from apps.accounts.models import AdminRole, AdminUser
    from apps.audit.models import OperationLog
    from apps.imports.forms import MAX_EXCEL_UPLOAD_SIZE
    from apps.imports.import_service import PRE_IMPORT_DATABASE_FILENAME
    from apps.imports.models import ImportBatch, ImportStatus
    from apps.imports.snapshots import (
        PREVIEW_FILENAME,
        PREVIEW_HASH_FILENAME,
        ROLLBACK_FILENAME,
        ROLLBACK_HASH_FILENAME,
    )
    from apps.imports.storage import artifact_path, verified_original_path
    from apps.materials.models import (
        ApplicationRecord,
        IdeologicalReport,
        IdeologicalReportSummary,
    )
    from apps.students.models import PartyBranch, Student

    settings.MEDIA_ROOT = media_root
    if "testserver" not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append("testserver")

    started = time.perf_counter()
    timings: dict[str, float] = {}
    call_command("migrate", verbosity=0, interactive=False)
    call_command("initialize_branches", verbosity=0)
    admin = AdminUser.objects.create_user(
        username="acceptance-data-admin",
        password="synthetic-only-password",
        display_name="合成验收管理员",
        role=AdminRole.DATA_ADMIN,
    )
    client = Client()
    client.force_login(admin)

    negative_results = _exercise_negative_uploads(
        client,
        dataset,
        max_upload_size=MAX_EXCEL_UPLOAD_SIZE,
        ImportBatch=ImportBatch,
        reverse=reverse,
        SimpleUploadedFile=SimpleUploadedFile,
    )

    first_started = time.perf_counter()
    first_batch = _upload_workbook(
        client,
        Path(dataset.first_workbook),
        ImportBatch=ImportBatch,
        reverse=reverse,
        SimpleUploadedFile=SimpleUploadedFile,
    )
    _assert_batch_preview(first_batch, dataset)
    response = client.post(reverse("imports:confirm", args=[first_batch.pk]))
    _require(response.status_code == 302, f"第一次确认导入失败：HTTP {response.status_code}")
    first_batch.refresh_from_db()
    _require(first_batch.status == ImportStatus.SUCCESS, "第一次导入批次状态不是success。")
    _require(Student.objects.count() == student_count, "第一次导入学生数量不匹配。")
    _require(ApplicationRecord.objects.count() == student_count, "申请记录数量不匹配。")
    _require(IdeologicalReportSummary.objects.count() == student_count, "思想汇报汇总数量不匹配。")
    _require(IdeologicalReport.objects.filter(is_active=True).count() == student_count * 3, "思想汇报明细数量不匹配。")
    timings["first_import_seconds"] = time.perf_counter() - first_started

    sample = Student.objects.select_related("branch").order_by("student_number").first()
    _require(sample is not None, "未找到抽查学生。")
    original_position = sample.position
    _exercise_query_paths(client, sample, reverse=reverse, Client=Client)

    second_started = time.perf_counter()
    second_batch = _upload_workbook(
        client,
        Path(dataset.second_workbook),
        ImportBatch=ImportBatch,
        reverse=reverse,
        SimpleUploadedFile=SimpleUploadedFile,
    )
    _assert_batch_preview(second_batch, dataset)
    response = client.post(reverse("imports:confirm", args=[second_batch.pk]))
    _require(response.status_code == 302, f"第二次确认导入失败：HTTP {response.status_code}")
    second_batch.refresh_from_db()
    sample.refresh_from_db()
    _require(second_batch.status == ImportStatus.SUCCESS, "第二次导入批次状态不是success。")
    _require(sample.position == "第二次导入职务", "第二次导入未覆盖抽查学生职务。")
    timings["second_import_seconds"] = time.perf_counter() - second_started

    rollback_started = time.perf_counter()
    preview_response = client.get(reverse("imports:rollback", args=[second_batch.pk]))
    _require(preview_response.status_code == 200, "回滚预览失败。")
    response = client.post(
        reverse("imports:rollback", args=[second_batch.pk]),
        {"confirm_batch_id": str(second_batch.pk)},
    )
    _require(response.status_code == 302, f"正式回滚失败：HTTP {response.status_code}")
    second_batch.refresh_from_db()
    sample.refresh_from_db()
    _require(second_batch.status == ImportStatus.ROLLED_BACK, "第二批次未标记为rolled_back。")
    _require(sample.position == original_position, "回滚后抽查学生职务未恢复。")
    _require(Student.objects.count() == student_count, "回滚后学生数量不匹配。")
    _require(IdeologicalReport.objects.filter(is_active=True).count() == student_count * 3, "回滚后思想汇报数量不匹配。")
    timings["rollback_seconds"] = time.perf_counter() - rollback_started

    evidence = {}
    for batch in (first_batch, second_batch):
        paths = [
            verified_original_path(batch),
            artifact_path(batch.pk, PREVIEW_FILENAME),
            artifact_path(batch.pk, PREVIEW_HASH_FILENAME),
            artifact_path(batch.pk, ROLLBACK_FILENAME),
            artifact_path(batch.pk, ROLLBACK_HASH_FILENAME),
            artifact_path(batch.pk, PRE_IMPORT_DATABASE_FILENAME),
        ]
        _require(all(path.is_file() and path.stat().st_size > 0 for path in paths), "批次证据缺失或为空。")
        evidence[str(batch.pk)] = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
        }

    audit_counts = {
        action: OperationLog.objects.filter(action=action).count()
        for action in ("upload_excel", "confirm_import", "rollback_import", "view_student_detail")
    }
    _require(audit_counts["confirm_import"] == 2, "确认导入审计数量不匹配。")
    _require(audit_counts["rollback_import"] == 1, "回滚审计数量不匹配。")

    report_path = output_directory / "acceptance_report.json"
    report = {
        "schema_version": 1,
        "git_sha": _git_sha(),
        "seed": seed,
        "student_count": student_count,
        "branch_count": PartyBranch.objects.filter(is_active=True).count(),
        "first_batch_id": first_batch.pk,
        "second_batch_id": second_batch.pk,
        "first_batch_status": first_batch.status,
        "second_batch_status": second_batch.status,
        "batch_statistics": {
            "first": _batch_statistics(first_batch),
            "second": _batch_statistics(second_batch),
        },
        "database_counts_after_rollback": {
            "students": Student.objects.count(),
            "applications": ApplicationRecord.objects.count(),
            "report_summaries": IdeologicalReportSummary.objects.count(),
            "active_reports": IdeologicalReport.objects.filter(is_active=True).count(),
        },
        "warning_rows_per_main_batch": dataset.warning_rows,
        "negative_results": negative_results,
        "audit_counts": audit_counts,
        "evidence_sha256": evidence,
        "sample_student_number": sample.student_number,
        "sample_restored_position": sample.position,
        "timings": {**timings, "total_seconds": time.perf_counter() - started},
        "database_path": str(database_path.resolve()),
        "media_root": str(media_root.resolve()),
        "restart_verified": False,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    connections.close_all()
    _run_restart_verification(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["restart_verified"] = True
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def verify_after_restart(report_path: Path) -> None:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    _configure_django(Path(report["database_path"]))
    from django.conf import settings

    settings.MEDIA_ROOT = Path(report["media_root"])
    from apps.imports.import_service import PRE_IMPORT_DATABASE_FILENAME
    from apps.imports.models import ImportBatch, ImportStatus
    from apps.imports.snapshots import PREVIEW_FILENAME, ROLLBACK_FILENAME
    from apps.imports.storage import artifact_path, verified_original_path
    from apps.materials.models import IdeologicalReport
    from apps.students.models import Student

    _require(_git_sha() == report["git_sha"], "重启复查代码SHA与验收报告不一致。")
    _require(Student.objects.count() == report["student_count"], "重启后学生数量不一致。")
    sample = Student.objects.get(student_number=report["sample_student_number"])
    _require(sample.position == report["sample_restored_position"], "重启后回滚恢复值不一致。")
    _require(IdeologicalReport.objects.filter(is_active=True).count() == report["student_count"] * 3, "重启后思想汇报数量不一致。")
    first = ImportBatch.objects.get(pk=report["first_batch_id"])
    second = ImportBatch.objects.get(pk=report["second_batch_id"])
    _require(first.status == ImportStatus.SUCCESS, "重启后第一批次状态不一致。")
    _require(second.status == ImportStatus.ROLLED_BACK, "重启后第二批次状态不一致。")
    for batch in (first, second):
        for path in (
            verified_original_path(batch),
            artifact_path(batch.pk, PREVIEW_FILENAME),
            artifact_path(batch.pk, ROLLBACK_FILENAME),
            artifact_path(batch.pk, PRE_IMPORT_DATABASE_FILENAME),
        ):
            _require(path.is_file() and path.stat().st_size > 0, "重启后证据文件不可用。")


def _exercise_negative_uploads(client, dataset: AcceptanceDataset, **deps) -> dict:
    ImportBatch = deps["ImportBatch"]
    reverse = deps["reverse"]
    SimpleUploadedFile = deps["SimpleUploadedFile"]
    max_upload_size = deps["max_upload_size"]
    results = {}
    for label, path in (
        ("invalid", Path(dataset.invalid_workbook)),
        ("duplicate", Path(dataset.duplicate_workbook)),
    ):
        batch = _upload_workbook(
            client,
            path,
            ImportBatch=ImportBatch,
            reverse=reverse,
            SimpleUploadedFile=SimpleUploadedFile,
        )
        response = client.post(reverse("imports:confirm", args=[batch.pk]))
        _require(response.status_code == 409, f"{label}负向批次未被409拒绝。")
        results[label] = {
            "batch_id": batch.pk,
            "errors": batch.error_records.count(),
            "warnings": batch.warning_records.count(),
            "confirm_status": response.status_code,
        }
    wrong = SimpleUploadedFile("wrong.xls", b"not-xlsx")
    results["wrong_extension_status"] = client.post(
        reverse("imports:upload"), {"excel_file": wrong}
    ).status_code
    oversized = SimpleUploadedFile("oversized.xlsx", b"x" * (max_upload_size + 1))
    results["oversized_status"] = client.post(
        reverse("imports:upload"), {"excel_file": oversized}
    ).status_code
    _require(results["wrong_extension_status"] == 400, "错误扩展名未被400拒绝。")
    _require(results["oversized_status"] == 400, "超限文件未被400拒绝。")
    return results


def _upload_workbook(client, path: Path, **deps):
    ImportBatch = deps["ImportBatch"]
    reverse = deps["reverse"]
    SimpleUploadedFile = deps["SimpleUploadedFile"]
    before_ids = set(ImportBatch.objects.values_list("pk", flat=True))
    uploaded = SimpleUploadedFile(
        path.name,
        path.read_bytes(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response = client.post(reverse("imports:upload"), {"excel_file": uploaded})
    _require(response.status_code == 302, f"上传{path.name}失败：HTTP {response.status_code}")
    return ImportBatch.objects.exclude(pk__in=before_ids).get()


def _assert_batch_preview(batch, dataset: AcceptanceDataset) -> None:
    _require(batch.total_sheets == 9, "主批次工作表数量不匹配。")
    _require(batch.success_sheets == 9 and batch.failed_sheets == 0, "主批次工作表状态不匹配。")
    _require(batch.total_rows == dataset.student_count, "主批次总行数不匹配。")
    _require(batch.success_rows == dataset.student_count, "主批次有效行数不匹配。")
    _require(batch.skipped_rows == 0, "主批次不应存在跳过行。")
    _require(batch.warning_rows == dataset.warning_rows, "主批次警告行数不匹配。")


def _batch_statistics(batch) -> dict[str, int]:
    return {
        field: getattr(batch, field)
        for field in (
            "total_sheets",
            "success_sheets",
            "failed_sheets",
            "total_rows",
            "success_rows",
            "skipped_rows",
            "warning_rows",
            "created_students",
            "updated_students",
            "created_reports",
            "updated_applications",
            "count_mismatch_rows",
            "unknown_branch_rows",
            "invalid_stage_rows",
            "column_shift_rows",
        )
    }


def _exercise_query_paths(admin_client, sample, *, reverse, Client) -> None:
    list_response = admin_client.get(
        reverse("students:admin_student_list"),
        {"student_number": sample.student_number},
    )
    _require(list_response.status_code == 200, "管理员学生查询失败。")
    _require(sample.student_number in list_response.content.decode("utf-8"), "管理员查询未返回抽查学生。")
    detail = admin_client.get(reverse("students:admin_student_detail", args=[sample.pk]))
    _require(detail.status_code == 200, "管理员学生详情失败。")
    student_client = Client()
    login = student_client.post(
        reverse("accounts:student_login"),
        {"name": sample.name, "student_number": sample.student_number},
    )
    _require(login.status_code == 302, "学生登录失败。")
    profile = student_client.get(reverse("students:student_profile"))
    _require(profile.status_code == 200, "学生本人查询失败。")
    _require(sample.student_number in profile.content.decode("utf-8"), "学生页面未展示本人学号。")


def _run_restart_verification(report_path: Path) -> None:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--verify-report",
        str(report_path.resolve()),
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def _git_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
    ).strip()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description="运行Excel约1500条同路径联合验收。")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--student-count", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=20260822)
    parser.add_argument("--verify-report", type=Path)
    args = parser.parse_args()
    if args.verify_report:
        verify_after_restart(args.verify_report.resolve())
        print("重启后持久性复查通过。")
        return
    if args.output_dir is None:
        parser.error("运行验收时必须提供 --output-dir。")
    report_path = run_acceptance(
        args.output_dir.resolve(),
        student_count=args.student_count,
        seed=args.seed,
    )
    print(f"联合验收通过：{report_path}")


if __name__ == "__main__":
    main()
