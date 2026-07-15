from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.materials.models import ApplicationRecord, IdeologicalReport, IdeologicalReportSummary
from apps.students.models import DevelopmentStage, PartyBranch, Student


DEMO_STUDENTS: tuple[dict[str, object], ...] = (
    {"name": "测试学生一", "student_number": "T20260001", "branch": "MINGLI", "stage": DevelopmentStage.ACTIVIST},
    {"name": "测试学生二", "student_number": "T20260002", "branch": "DELI", "stage": DevelopmentStage.PROBATIONARY},
    {"name": "测试学生三", "student_number": "T20260003", "branch": "WEILI", "stage": DevelopmentStage.FULL_MEMBER},
    {"name": "测试学生四", "student_number": "T20260004", "branch": "QIULI", "stage": DevelopmentStage.ACTIVIST},
)


class Command(BaseCommand):
    help = "Seed idempotent fictional demo data for local development."

    def handle(self, *args: object, **options: object) -> None:
        call_command("initialize_branches")
        created_students = 0
        for index, item in enumerate(DEMO_STUDENTS, start=1):
            branch = PartyBranch.objects.get(code=item["branch"])
            student, created = Student.objects.update_or_create(
                student_number=item["student_number"],
                defaults={
                    "name": item["name"],
                    "branch": branch,
                    "development_stage": item["stage"],
                    "position": "班级骨干" if index % 2 else "",
                },
            )
            created_students += int(created)

            if index != 4:
                ApplicationRecord.objects.update_or_create(
                    student=student,
                    defaults={"applied_at": date(2025, index, min(index + 10, 28))},
                )

            IdeologicalReportSummary.objects.update_or_create(
                student=student,
                defaults={"reported_total_count": 2 if index != 2 else None, "calculated_date_count": 2},
            )

            # 测试数据只覆盖关系形态，不模拟正式导入流程。
            for sequence in (1, 2):
                IdeologicalReport.objects.update_or_create(
                    student=student,
                    sequence_number=sequence,
                    is_active=True,
                    defaults={
                        "submitted_at": date(2025, sequence + index, 15),
                        "source_column_name": f"第{sequence}次思想汇报",
                    },
                )

        self.stdout.write(self.style.SUCCESS(f"Seeded demo data. created_students={created_students}"))
