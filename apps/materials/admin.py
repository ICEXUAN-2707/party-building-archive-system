from django.contrib import admin

from apps.audit.admin import AuditedModelAdmin

from .models import ApplicationRecord, IdeologicalReport, IdeologicalReportSummary


@admin.register(ApplicationRecord)
class ApplicationRecordAdmin(AuditedModelAdmin):
    list_display = ("student", "applied_at", "updated_at")
    list_filter = ("applied_at",)
    search_fields = ("student__name", "student__student_number")
    readonly_fields = ("created_at", "updated_at")


@admin.register(IdeologicalReportSummary)
class IdeologicalReportSummaryAdmin(AuditedModelAdmin):
    list_display = ("student", "reported_total_count", "calculated_date_count", "updated_at")
    search_fields = ("student__name", "student__student_number")
    readonly_fields = ("created_at", "updated_at")


@admin.register(IdeologicalReport)
class IdeologicalReportAdmin(AuditedModelAdmin):
    list_display = ("student", "sequence_number", "submitted_at", "is_active", "created_at")
    list_filter = ("is_active", "submitted_at")
    search_fields = ("student__name", "student__student_number", "source_column_name")
    readonly_fields = ("created_at",)
