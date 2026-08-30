from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tarfile
import tempfile

from django.conf import settings
from django.db import connection


class BackupError(RuntimeError):
    pass


@dataclass(frozen=True)
class BackupResult:
    archive_path: Path
    sha256_path: Path
    manifest_path: Path
    sha256: str


def create_full_backup(*, reason: str = "daily", now: datetime | None = None) -> BackupResult:
    if reason not in {"daily", "import-before", "import-after", "manual"}:
        raise BackupError("不支持的备份原因。")
    if connection.vendor != "sqlite":
        raise BackupError("周期备份只支持SQLite。")

    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    backup_root = Path(settings.BACKUP_ROOT).resolve()
    media_root = Path(settings.MEDIA_ROOT).resolve()
    backup_root.mkdir(parents=True, exist_ok=True)
    basename = f"party-archive-{reason}-{stamp}"
    final_archive = backup_root / f"{basename}.tar.gz"
    final_hash = backup_root / f"{basename}.sha256"
    final_manifest = backup_root / f"{basename}.manifest.json"
    if any(path.exists() for path in (final_archive, final_hash, final_manifest)):
        raise BackupError("同名备份已经存在。")

    with tempfile.TemporaryDirectory(prefix=".backup-", dir=backup_root) as temporary:
        staging = Path(temporary)
        database_backup = staging / "database.sqlite3"
        _backup_sqlite(database_backup)
        media_entries = _media_manifest(media_root)
        manifest = {
            "schema_version": 1,
            "created_at": now.isoformat(),
            "reason": reason,
            "release": os.environ.get("PARTY_ARCHIVE_RELEASE", "unknown"),
            "database": {
                "path": "database.sqlite3",
                "size": database_backup.stat().st_size,
                "sha256": _sha256(database_backup),
            },
            "media_root": "media",
            "media_files": media_entries,
        }
        staged_manifest = staging / "manifest.json"
        staged_manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary_archive = staging / "archive.tar.gz"
        with tarfile.open(temporary_archive, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            archive.add(database_backup, arcname="database.sqlite3", recursive=False)
            archive.add(staged_manifest, arcname="manifest.json", recursive=False)
            for entry in media_entries:
                source = media_root / entry["path"]
                archive.add(source, arcname=f"media/{entry['path']}", recursive=False)
        archive_hash = _sha256(temporary_archive)
        os.replace(temporary_archive, final_archive)
        _atomic_text(final_hash, f"{archive_hash}  {final_archive.name}\n")
        _atomic_text(final_manifest, json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    return BackupResult(final_archive, final_hash, final_manifest, archive_hash)


def verify_full_backup(archive_path: Path) -> dict[str, object]:
    archive_path = archive_path.resolve()
    hash_path = archive_path.with_suffix("").with_suffix(".sha256")
    expected = hash_path.read_text(encoding="ascii").split()[0]
    if _sha256(archive_path) != expected:
        raise BackupError("备份归档SHA-256校验失败。")
    with tempfile.TemporaryDirectory(prefix="party-archive-verify-") as temporary:
        target = Path(temporary)
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            if any(member.issym() or member.islnk() or Path(member.name).is_absolute() or ".." in Path(member.name).parts for member in members):
                raise BackupError("备份归档包含不安全路径。")
            archive.extractall(target, filter="data")
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        database = target / "database.sqlite3"
        if _sha256(database) != manifest["database"]["sha256"]:
            raise BackupError("备份数据库摘要不一致。")
        _verify_sqlite(database)
        for entry in manifest["media_files"]:
            media_file = target / "media" / entry["path"]
            if not media_file.is_file() or _sha256(media_file) != entry["sha256"]:
                raise BackupError("备份媒体摘要不一致。")
    return manifest


def prune_local_backups(*, daily_keep: int = 7, import_keep: int = 10) -> list[Path]:
    root = Path(settings.BACKUP_ROOT).resolve()
    removed: list[Path] = []
    groups = {"daily": daily_keep, "import-": import_keep}
    for marker, keep in groups.items():
        archives = sorted(root.glob(f"party-archive-{marker}*.tar.gz"), reverse=True)
        for archive in archives[keep:]:
            companions = [archive, archive.with_suffix("").with_suffix(".sha256"), archive.with_suffix("").with_suffix(".manifest.json")]
            for path in companions:
                if path.exists():
                    path.unlink()
                    removed.append(path)
    return removed


def _backup_sqlite(destination: Path) -> None:
    connection.ensure_connection()
    source = connection.connection
    if not isinstance(source, sqlite3.Connection):
        raise BackupError("无法访问SQLite连接。")
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
        target.commit()
    finally:
        target.close()
    _verify_sqlite(destination)


def _verify_sqlite(path: Path) -> None:
    database = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        if database.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise BackupError("SQLite完整性检查失败。")
    finally:
        database.close()


def _media_manifest(media_root: Path) -> list[dict[str, object]]:
    if not media_root.exists():
        return []
    entries: list[dict[str, object]] = []
    for path in sorted(media_root.rglob("*")):
        if path.is_symlink():
            raise BackupError("媒体目录包含符号链接。")
        if not path.is_file():
            continue
        resolved = path.resolve()
        if media_root not in resolved.parents:
            raise BackupError("媒体文件越出持久化目录。")
        entries.append({"path": path.relative_to(media_root).as_posix(), "size": path.stat().st_size, "sha256": _sha256(path)})
    return entries


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_text(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)
