from django.contrib import admin

from .models import ImportBatch, ImportErrorRecord, ImportWarningRecord


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_label", "original_filename", "status", "imported_by", "imported_at")
    list_filter = ("status", "imported_at")
    search_fields = ("batch_label", "original_filename", "file_hash")
    readonly_fields = ("failure_message", "rolled_back_at")


@admin.register(ImportErrorRecord)
class ImportErrorRecordAdmin(admin.ModelAdmin):
    list_display = ("import_batch", "sheet_name", "excel_row_number", "field_name", "error_code")
    list_filter = ("error_code", "sheet_name")
    search_fields = ("student_name", "student_number", "error_message")
    readonly_fields = ("created_at",)


@admin.register(ImportWarningRecord)
class ImportWarningRecordAdmin(admin.ModelAdmin):
    list_display = ("import_batch", "sheet_name", "excel_row_number", "warning_code")
    list_filter = ("warning_code", "sheet_name")
    search_fields = ("student_name", "student_number", "warning_message")
    readonly_fields = ("created_at",)
