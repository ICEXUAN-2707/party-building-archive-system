from django.core.validators import MinValueValidator
from django.db import models


class ApplicationRecord(models.Model):
    student = models.OneToOneField(
        "students.Student",
        verbose_name="学生",
        related_name="application_record",
        on_delete=models.CASCADE,
    )
    applied_at = models.DateField("申请入党时间", null=True, blank=True)
    source_import_batch = models.ForeignKey(
        "imports.ImportBatch",
        verbose_name="来源导入批次",
        related_name="application_records",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "申请入党记录"
        verbose_name_plural = "申请入党记录"
        ordering = ["student__student_number"]

    def __str__(self) -> str:
        return f"{self.student} 申请入党记录"


class IdeologicalReportSummary(models.Model):
    student = models.OneToOneField(
        "students.Student",
        verbose_name="学生",
        related_name="report_summary",
        on_delete=models.CASCADE,
    )
    reported_total_count = models.PositiveIntegerField("Excel填报总篇数", null=True, blank=True)
    calculated_date_count = models.PositiveIntegerField("系统计算日期数", default=0)
    source_import_batch = models.ForeignKey(
        "imports.ImportBatch",
        verbose_name="来源导入批次",
        related_name="report_summaries",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "思想汇报汇总"
        verbose_name_plural = "思想汇报汇总"
        ordering = ["student__student_number"]

    def __str__(self) -> str:
        return f"{self.student} 思想汇报汇总"


class IdeologicalReport(models.Model):
    student = models.ForeignKey(
        "students.Student",
        verbose_name="学生",
        related_name="ideological_reports",
        on_delete=models.CASCADE,
    )
    sequence_number = models.PositiveIntegerField("思想汇报次数", validators=[MinValueValidator(1)])
    submitted_at = models.DateField("提交时间")
    source_column_name = models.CharField("Excel来源列名", max_length=128)
    import_batch = models.ForeignKey(
        "imports.ImportBatch",
        verbose_name="导入批次",
        related_name="ideological_reports",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    is_active = models.BooleanField("是否有效", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "思想汇报明细"
        verbose_name_plural = "思想汇报明细"
        ordering = ["student__student_number", "sequence_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "sequence_number", "is_active"],
                name="unique_active_report_sequence",
            )
        ]
        indexes = [
            models.Index(fields=["student", "sequence_number"]),
            models.Index(fields=["submitted_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} 第{self.sequence_number}次思想汇报"
