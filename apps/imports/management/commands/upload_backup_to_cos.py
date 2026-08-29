from pathlib import Path
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.imports.backup_service import BackupError, verify_full_backup
from apps.imports.cos_backup import CosBackupError, upload_verified_backup


class Command(BaseCommand):
    help = "校验本机备份后上传到启用版本控制和SSE-COS的私有存储桶。"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("archive", type=Path)

    def handle(self, *args: object, **options: object) -> None:
        archive = options["archive"].resolve()
        backup_root = Path(settings.BACKUP_ROOT).resolve()
        if backup_root not in archive.parents:
            raise CommandError("只允许上传生产备份目录中的归档。")
        try:
            verify_full_backup(archive)
            result = upload_verified_backup(archive)
            marker = backup_root / ".last-offsite-success"
            temporary_marker = marker.with_name(f".{marker.name}.tmp-{os.getpid()}")
            temporary_marker.write_text(
                f"object={result.object_key}\nversion={result.version_id}\nsha256={result.sha256}\n",
                encoding="utf-8",
            )
            os.replace(temporary_marker, marker)
        except (BackupError, CosBackupError, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"COS备份验证通过：{result.object_key}\n版本ID：{result.version_id}\nSHA-256：{result.sha256}"
        ))
