from pathlib import Path

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.imports.backup_service import BackupError, create_full_backup, prune_local_backups, verify_full_backup


class Command(BaseCommand):
    help = "创建、校验并按保留策略清理生产SQLite和媒体完整备份。"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--reason", choices=["daily", "import-before", "import-after", "manual"], default="daily")
        parser.add_argument("--verify", type=Path, help="只验证指定归档，不创建备份。")
        parser.add_argument("--no-prune", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        try:
            if options["verify"]:
                manifest = verify_full_backup(options["verify"])
                self.stdout.write(self.style.SUCCESS(f"备份验证通过：{options['verify']}；原因：{manifest['reason']}"))
                return
            result = create_full_backup(reason=options["reason"])
            verify_full_backup(result.archive_path)
            removed = [] if options["no_prune"] else prune_local_backups()
        except (BackupError, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"备份完成：{result.archive_path}\nSHA-256：{result.sha256}\n清理文件数：{len(removed)}"
        ))
