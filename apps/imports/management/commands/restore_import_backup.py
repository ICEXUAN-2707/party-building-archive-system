from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.imports.disaster_restore import (
    DisasterRestoreError,
    restore_disaster_backup,
    verify_disaster_restore,
)
from apps.imports.models import ImportBatch


class Command(BaseCommand):
    help = "校验或在停机状态下恢复指定导入批次的SQLite导入前备份。"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--batch-id", type=int, required=True)
        parser.add_argument(
            "--verify-only",
            action="store_true",
            help="只校验证据、批次绑定和数据库完整性（默认行为）。",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="执行数据库文件恢复。",
        )
        parser.add_argument(
            "--maintenance-mode",
            action="store_true",
            help="确认Web及其他数据库进程已停止。",
        )

    def handle(self, *args: object, **options: object) -> None:
        if options["verify_only"] and options["confirm"]:
            raise CommandError("--verify-only 与 --confirm 不能同时使用。")
        try:
            batch = ImportBatch.objects.get(pk=options["batch_id"])
        except ImportBatch.DoesNotExist as exc:
            raise CommandError("指定导入批次不存在。") from exc

        try:
            if not options["confirm"]:
                verification = verify_disaster_restore(batch)
                self.stdout.write(
                    self.style.SUCCESS(
                        "校验通过；未修改数据库。\n"
                        f"批次：{verification.batch_id}\n"
                        f"恢复源：{verification.backup_path}\n"
                        f"SHA-256：{verification.backup_sha256}"
                    )
                )
                return
            if not options["maintenance_mode"]:
                raise CommandError(
                    "执行恢复必须同时提供 --maintenance-mode，确认Web和其他数据库进程已停止。"
                )
            result = restore_disaster_backup(batch)
        except DisasterRestoreError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "SQLite灾难恢复完成。\n"
                f"恢复批次：{result.verification.batch_id}\n"
                f"恢复前保护备份：{result.safety_backup_path}\n"
                f"保护备份哈希：{result.safety_backup_sha256_path}\n"
                "下一步必须执行：manage.py migrate --check、manage.py check及业务一致性验证。"
            )
        )
