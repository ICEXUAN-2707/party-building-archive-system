from __future__ import annotations

import logging
from collections.abc import Iterable

from django.db import transaction
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from apps.accounts.permissions import (
    data_admin_required,
    viewer_or_data_admin_required,
)
from apps.audit.services import record_operation_log
from apps.imports import error_codes
from apps.imports.datatypes import ParseError, ParseResult, ParseWarning
from apps.imports.forms import ExcelUploadForm
from apps.imports.import_service import ConfirmImportConflict, ConfirmImportFailed, confirm_import
from apps.imports.models import ImportBatch, ImportErrorRecord, ImportWarningRecord
from apps.imports.parser import parse_workbook
from apps.imports.snapshots import build_preview_snapshot, load_preview_snapshot, write_preview_snapshot
from apps.imports.storage import (
    ImportEvidenceIntegrityError,
    ImportEvidenceNotFound,
    open_verified_original,
    remove_batch_directory,
    sanitize_original_filename,
    store_uploaded_file,
)


logger = logging.getLogger(__name__)


class PreviewPersistenceError(Exception):
    """解析结果无法无损映射到当前冻结模型。"""


@data_admin_required
@require_http_methods(["GET", "POST"])
def upload(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        return render(request, "imports/upload.html", {"form": ExcelUploadForm()})

    form = ExcelUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "imports/upload.html", {"form": form}, status=400)

    try:
        batch = _create_preview_batch(request, form.cleaned_data["excel_file"])
    except Exception:
        logger.exception("Excel上传预览生成失败")
        form.add_error(None, "文件无法安全解析或保存，请检查Excel内容后重新上传。")
        return render(request, "imports/upload.html", {"form": form}, status=400)
    return redirect("imports:preview", batch_id=batch.pk)


@data_admin_required
@require_GET
def preview(request: HttpRequest, batch_id: int) -> HttpResponse:
    batch = get_object_or_404(
        ImportBatch.objects.select_related("imported_by"),
        pk=batch_id,
    )
    try:
        snapshot = load_preview_snapshot(batch)
    except ImportEvidenceNotFound as exc:
        raise Http404("预览证据不存在。") from exc
    except ImportEvidenceIntegrityError:
        return render(
            request,
            "imports/preview.html",
            {
                "batch": batch,
                "evidence_error": "预览证据完整性校验失败，已拒绝展示。",
            },
            status=409,
        )

    return render(
        request,
        "imports/preview.html",
        {
            "batch": batch,
            "snapshot": snapshot,
            "statistics": snapshot["statistics"],
            "sheet_results": snapshot["sheet_results"],
            "valid_rows": _display_rows(snapshot["valid_rows"]),
            "conflicts": snapshot["conflicts"],
            "errors": batch.error_records.all(),
            "warnings": batch.warning_records.all(),
        },
    )


@data_admin_required
@require_POST
def confirm(request: HttpRequest, batch_id: int) -> HttpResponse:
    """校验冻结证据并执行整批原子导入。"""
    if not ImportBatch.objects.filter(pk=batch_id).exists():
        raise Http404("导入批次不存在。")
    try:
        batch = confirm_import(request, batch_id)
    except (ConfirmImportConflict, ImportEvidenceNotFound, ImportEvidenceIntegrityError) as exc:
        return HttpResponse(str(exc), status=409)
    except ConfirmImportFailed:
        logger.exception("Excel正式导入失败", extra={"batch_id": batch_id})
        return HttpResponse("正式导入失败，业务数据未发生部分写入。", status=500)
    return redirect("imports:batch_detail", batch_id=batch.pk)


@viewer_or_data_admin_required
@require_GET
def history(request: HttpRequest) -> HttpResponse:
    batches = ImportBatch.objects.select_related("imported_by").all()
    return render(request, "imports/history.html", {"batches": batches})


@viewer_or_data_admin_required
@require_GET
def batch_detail(request: HttpRequest, batch_id: int) -> HttpResponse:
    batch = get_object_or_404(
        ImportBatch.objects.select_related("imported_by", "rolled_back_by").prefetch_related(
            "error_records",
            "warning_records",
        ),
        pk=batch_id,
    )
    return render(
        request,
        "imports/batch_detail.html",
        {
            "batch": batch,
            "errors": batch.error_records.all(),
            "warnings": batch.warning_records.all(),
        },
    )


@data_admin_required
@require_GET
def download_file(request: HttpRequest, batch_id: int) -> HttpResponse:
    batch = get_object_or_404(ImportBatch, pk=batch_id)
    try:
        source = open_verified_original(batch)
    except ImportEvidenceNotFound as exc:
        raise Http404("原始Excel文件不存在。") from exc
    except ImportEvidenceIntegrityError:
        return HttpResponse("原始Excel完整性校验失败，已拒绝下载。", status=409)

    return FileResponse(
        source,
        as_attachment=True,
        filename=batch.original_filename,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _create_preview_batch(request: HttpRequest, uploaded_file) -> ImportBatch:
    batch_id: int | None = None
    try:
        with transaction.atomic():
            now = timezone.localtime()
            batch = ImportBatch.objects.create(
                batch_label=f"Excel预览 {now:%Y%m%d-%H%M%S}",
                original_filename=sanitize_original_filename(uploaded_file.name),
                imported_by=request.user,
            )
            batch_id = batch.pk

            stored = store_uploaded_file(batch, uploaded_file)
            batch.stored_file.name = stored.relative_name
            batch.file_hash = stored.sha256

            result = parse_workbook(stored.absolute_path)
            _persist_parse_records(batch, result)
            _apply_statistics(batch, result)
            batch.save()

            snapshot = build_preview_snapshot(batch, result)
            write_preview_snapshot(batch, snapshot)
            record_operation_log(
                request,
                action="upload_excel",
                target_type="ImportBatch",
                target_id=str(batch.pk),
                description=f"上传Excel并生成服务端预览：{batch.original_filename}",
            )
        return batch
    except Exception:
        if batch_id is not None:
            try:
                remove_batch_directory(batch_id)
            except Exception:
                logger.exception("清理失败的导入批次目录时发生异常", extra={"batch_id": batch_id})
        raise


def _persist_parse_records(batch: ImportBatch, result: ParseResult) -> None:
    error_records = [_error_record(batch, error) for error in result.errors]
    warning_records = [_warning_record(batch, warning) for warning in result.warnings]
    ImportErrorRecord.objects.bulk_create(error_records)
    ImportWarningRecord.objects.bulk_create(warning_records)


def _error_record(batch: ImportBatch, error: ParseError) -> ImportErrorRecord:
    if (
        not isinstance(error.excel_row_number, int)
        or isinstance(error.excel_row_number, bool)
        or error.excel_row_number <= 0
    ):
        raise PreviewPersistenceError(
            "当前模型无法无损保存缺少Excel行号的解析错误，已拒绝生成预览批次。"
        )
    return ImportErrorRecord(
        import_batch=batch,
        sheet_name=_clip(error.sheet_name, 128),
        excel_row_number=error.excel_row_number,
        student_name=_clip(error.student_name, 64),
        student_number=_clip(error.student_number, 32),
        field_name=_clip(error.field_name, 128),
        error_code=_clip(error.code, 64),
        error_message=error.message,
    )


def _warning_record(batch: ImportBatch, warning: ParseWarning) -> ImportWarningRecord:
    if (
        not isinstance(warning.excel_row_number, int)
        or isinstance(warning.excel_row_number, bool)
        or warning.excel_row_number <= 0
    ):
        raise PreviewPersistenceError(
            "当前模型无法无损保存缺少Excel行号的解析警告，已拒绝生成预览批次。"
        )
    return ImportWarningRecord(
        import_batch=batch,
        sheet_name=_clip(warning.sheet_name, 128),
        excel_row_number=warning.excel_row_number,
        student_name=_clip(warning.student_name, 64),
        student_number=_clip(warning.student_number, 32),
        warning_code=_clip(warning.code, 64),
        warning_message=warning.message,
        source_value=_clip(warning.source_value, 255),
        parsed_value=_clip(warning.parsed_value, 255),
    )


def _apply_statistics(batch: ImportBatch, result: ParseResult) -> None:
    for field in (
        "total_sheets",
        "success_sheets",
        "failed_sheets",
        "total_rows",
        "success_rows",
        "skipped_rows",
        "warning_rows",
    ):
        setattr(batch, field, getattr(result, field))

    batch.count_mismatch_rows = _distinct_record_rows(
        result.warnings,
        error_codes.WARNING_REPORT_COUNT_MISMATCH,
    )
    batch.unknown_branch_rows = _distinct_record_rows(
        result.errors,
        error_codes.ERROR_UNKNOWN_SHEET,
    )
    batch.invalid_stage_rows = _distinct_record_rows(
        result.errors,
        error_codes.ERROR_ROW_INVALID_STAGE,
    )
    batch.column_shift_rows = _distinct_record_rows(
        result.errors,
        error_codes.ERROR_ROW_COLUMN_SHIFT_SUSPECTED,
    )


def _distinct_record_rows(records: Iterable[ParseError | ParseWarning], code: str) -> int:
    return len(
        {
            (record.sheet_name, record.excel_row_number)
            for record in records
            if record.code == code
        }
    )


def _clip(value: object, maximum: int) -> str:
    return str(value or "")[:maximum]


def _display_rows(rows: list[dict]) -> list[dict]:
    display_rows: list[dict] = []
    for row in rows:
        display_row = row.copy()
        display_row["applied_at"] = parse_date(row["applied_at"]) if row["applied_at"] else None
        display_row["report_items"] = [
            {
                **item,
                "submitted_at": parse_date(item["submitted_at"]),
            }
            for item in row["report_items"]
        ]
        display_rows.append(display_row)
    return display_rows
