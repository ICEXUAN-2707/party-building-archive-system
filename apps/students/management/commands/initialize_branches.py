from django.core.management.base import BaseCommand

from apps.students.models import PartyBranch


BRANCHES: tuple[tuple[str, str], ...] = (
    ("MINGLI", "明理党支部"),
    ("DELI", "德理党支部"),
    ("WEILI", "惟理党支部"),
    ("QIULI", "求理党支部"),
    ("ZHILI", "知理党支部"),
    ("ZHAOLI", "昭理党支部"),
    ("XUELI", "学理党支部"),
    ("BOLI", "博理党支部"),
    ("YILI", "艺理党支部"),
)


class Command(BaseCommand):
    help = "Initialize the nine frozen party branches idempotently."

    def handle(self, *args: object, **options: object) -> None:
        created_count = 0
        updated_count = 0
        for code, name in BRANCHES:
            branch, created = PartyBranch.objects.update_or_create(
                code=code,
                defaults={"name": name, "is_active": True},
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Initialized party branches: created={created_count}, updated={updated_count}, total={PartyBranch.objects.count()}"
            )
        )
