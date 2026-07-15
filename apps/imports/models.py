from django.conf import settings
from django.db import models


class ImportStatus(models.TextChoices):
    PREVIEWED = "previewed", "已预览"
    SUCCESS = "success", "成功"
    FAILED = "failed", "失败"
    ROLLED_BACK = "rolled_back", "已回滚"


class ImportBatch(models.Model):
    batch_label = models.CharField("批次标签", max_length=128)
    original_filename = models.CharField("原始文件名", max_length=255)
    stored_file = models.FileField("保存文件", upload_to="imports/", blank=True)
    file_hash = models.CharField("文件哈希", max_length=128, blank=True)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="导入人",
        related_name="import_batches",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    imported_at = models.DateTimeField("导入时间", null=True, blank=True)
    status = models.CharField("批次状态", max_length=32, choices=ImportStatus.choices, default=ImportStatus.PREVIEWED)
    total_sheets = models.PositiveIntegerField("工作表总数", default=0)
    success_sheets = models.PositiveIntegerField("成功工作表数", default=0)
    failed_sheets = models.PositiveIntegerField("失败工作表数", default=0)
    total_rows = models.PositiveIntegerField("总行数", default=0)
    success_rows = models.PositiveIntegerField("成功行数", default=0)
    skipped_rows = models.PositiveIntegerField("跳过行数", default=0)
    warning_rows = models.PositiveIntegerField("警告行数", default=0)
    created_students = models.PositiveIntegerField("新增学生数", default=0)
    updated_students = models.PositiveIntegerField("更新学生数", default=0)
    created_reports = models.PositiveIntegerField("新增思想汇报数", default=0)
    updated_applications = models.PositiveIntegerField("更新申请记录数", default=0)
    count_mismatch_rows = models.PositiveIntegerField("总篇数不一致行数", default=0)
    unknown_branch_rows = models.PositiveIntegerField("未知支部行数", default=0)
    invalid_stage_rows = models.PositiveIntegerField("无效阶段行数", default=0)
    column_shift_rows = models.PositiveIntegerField("疑似列错位行数", default=0)
    rolled_back_at = models.DateTimeField("回滚时间", null=True, blank=True)
    rolled_back_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="回滚人",
        related_name="rolled_back_batches",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = "导入批次"
        verbose_name_plural = "导入批次"
        ordering = ["-imported_at", "-id"]

    def __str__(self) -> str:
        return self.batch_label


class ImportErrorRecord(models.Model):
    import_batch = models.ForeignKey(ImportBatch, verbose_name="导入批次", related_name="error_records", on_delete=models.CASCADE)
    sheet_name = models.CharField("工作表名称", max_length=128)
    excel_row_number = models.PositiveIntegerField("Excel行号")
    student_name = models.CharField("学生姓名", max_length=64, blank=True)
    student_number = models.CharField("学号", max_length=32, blank=True)
    field_name = models.CharField("字段名", max_length=128, blank=True)
    error_code = models.CharField("错误代码", max_length=64)
    error_message = models.TextField("错误说明")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "导入错误"
        verbose_name_plural = "导入错误"
        ordering = ["import_batch_id", "sheet_name", "excel_row_number"]

    def __str__(self) -> str:
        return f"{self.sheet_name}:{self.excel_row_number} {self.error_code}"


class ImportWarningRecord(models.Model):
    import_batch = models.ForeignKey(ImportBatch, verbose_name="导入批次", related_name="warning_records", on_delete=models.CASCADE)
    sheet_name = models.CharField("工作表名称", max_length=128)
    excel_row_number = models.PositiveIntegerField("Excel行号")
    student_name = models.CharField("学生姓名", max_length=64, blank=True)
    student_number = models.CharField("学号", max_length=32, blank=True)
    warning_code = models.CharField("警告代码", max_length=64)
    warning_message = models.TextField("警告说明")
    source_value = models.CharField("原始值", max_length=255, blank=True)
    parsed_value = models.CharField("解析值", max_length=255, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "导入警告"
        verbose_name_plural = "导入警告"
        ordering = ["import_batch_id", "sheet_name", "excel_row_number"]

    def __str__(self) -> str:
        return f"{self.sheet_name}:{self.excel_row_number} {self.warning_code}"
