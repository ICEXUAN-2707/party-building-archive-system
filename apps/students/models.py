from django.db import models
from django.utils import timezone


def get_default_submitted_date():
    return timezone.now().date()


class DevelopmentStage(models.TextChoices):
    ACTIVIST = "ACTIVIST", "入党积极分子"
    PROBATIONARY = "PROBATIONARY", "中共预备党员"
    FULL_MEMBER = "FULL_MEMBER", "正式党员"


class StudentStatus(models.TextChoices):
    ACTIVE = "active", "有效"
    INACTIVE = "inactive", "无效"


class PartyBranch(models.Model):
    name = models.CharField("支部名称", max_length=64, unique=True)
    code = models.CharField("支部代码", max_length=32, unique=True)
    is_active = models.BooleanField("是否启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "党支部"
        verbose_name_plural = "党支部"
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name


class Student(models.Model):
    name = models.CharField("姓名", max_length=64)
    student_number = models.CharField("学号", max_length=32, unique=True)
    branch = models.ForeignKey(
        PartyBranch,
        verbose_name="党支部",
        related_name="students",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    development_stage = models.CharField("发展阶段", max_length=32, choices=DevelopmentStage.choices)
    position = models.CharField("职务", max_length=128, blank=True)
    status = models.CharField(
        "学生状态",
        max_length=16,
        choices=StudentStatus.choices,
        default=StudentStatus.ACTIVE,
    )
    source_import_batch = models.ForeignKey(
        "imports.ImportBatch",
        verbose_name="来源导入批次",
        related_name="students",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "学生"
        verbose_name_plural = "学生"
        ordering = ["student_number"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["student_number"]),
            models.Index(fields=["development_stage"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name}（{self.student_number}）"


# 思想汇报模型，使用可序列化函数作为日期默认值，修复迁移序列化报错
class IdeologicalReport(models.Model):
    student = models.ForeignKey(
        Student,
        verbose_name="学生",
        related_name="reports",
        on_delete=models.CASCADE,
    )
    sequence_number = models.IntegerField("序号")
    submitted_at = models.DateField("提交时间", default=get_default_submitted_date)
    is_active = models.BooleanField("是否有效", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "思想汇报"
        verbose_name_plural = "思想汇报"
        ordering = ["sequence_number"]

    def __str__(self) -> str:
        return f"{self.student} - Report {self.sequence_number}"


# 独立入党申请模型，删除旧别名 ApplicationRecord=Student，解决TypeError
class ApplicationRecord(models.Model):
    student = models.ForeignKey(
        Student,
        verbose_name="学生",
        related_name="application_records",
        on_delete=models.CASCADE,
    )
    applied_at = models.DateField("申请时间")
    reported_total_count = models.IntegerField("填报总数", default=0)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "入党申请记录"
        verbose_name_plural = "入党申请记录"

    def __str__(self) -> str:
        return f"ApplicationRecord({self.student}, {self.applied_at})"
