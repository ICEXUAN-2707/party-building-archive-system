from django.contrib import admin

from apps.audit.admin import AuditedModelAdmin

from .models import PartyBranch, Student


@admin.register(PartyBranch)
class PartyBranchAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Student)
class StudentAdmin(AuditedModelAdmin):
    audit_target_type = "Student"
    list_display = ("student_number", "name", "branch", "development_stage", "status", "updated_at")
    list_filter = ("branch", "development_stage", "status")
    search_fields = ("student_number", "name")
    readonly_fields = ("created_at", "updated_at")
