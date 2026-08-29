from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.imports.backup_service import BackupError, verify_full_backup
from apps.imports.cos_backup import CosBackupError, download_versioned_backup


class Command(BaseCommand):
    help = "按COS版本ID下载备份，并在本地完成SHA及归档验证。"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--object-key", required=True)
        parser.add_argument("--version-id", required=True)
        parser.add_argument("--filename", required=True)

    def handle(self, *args: object, **options: object) -> None:
        filename = Path(options["filename"])
        if filename.name != str(filename) or not filename.name.endswith(".tar.gz"):
            raise CommandError("filename必须是无目录的.tar.gz文件名。")
        destination = Path(settings.BACKUP_ROOT).resolve() / "cos-restore" / filename.name
        try:
            download_versioned_backup(options["object_key"], options["version_id"], destination)
            manifest = verify_full_backup(destination)
        except (BackupError, CosBackupError, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"COS版本备份下载并验证通过：{destination}\n原因：{manifest['reason']}\n下一步：在隔离环境执行恢复演练。"
        ))
