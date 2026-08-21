from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.db import connections
from django.utils import timezone

from apps.imports.import_service import PRE_IMPORT_DATABASE_FILENAME, _confirmation_lock
from apps.imports.models import ImportBatch, ImportStatus
from apps.imports.storage import artifact_path


REQUIRED_TABLES = {
    "django_migrations",
    "imports_importbatch",
    "students_student",
    "materials_applicationrecord",
    "materials_ideologicalreportsummary",
    "materials_ideologicalreport",
}


class DisasterRestoreError(Exception):
    """灾难恢复校验或文件替换失败。"""


@dataclass(frozen=True)
class BackupVerification:
    batch_id: int
    backup_path: Path
    database_path: Path
    backup_sha256: str


@dataclass(frozen=True)
class DisasterRestoreResult:
    verification: BackupVerification
    safety_backup_path: Path
    safety_backup_sha256_path: Path


def verify_disaster_restore(batch: ImportBatch) -> BackupVerification:
    """只读校验灾难恢复源、批次绑定和当前SQLite目标。"""
    database_path = _configured_database_path()
    backup_path = _bound_backup_path(batch)
    if backup_path == database_path:
        raise DisasterRestoreError("恢复源与当前数据库路径相同，已拒绝执行。")
    _verify_sqlite_database(database_path, require_batch=None)
    _verify_sqlite_database(backup_path, require_batch=batch)
    return BackupVerification(
        batch_id=batch.pk,
        backup_path=backup_path,
        database_path=database_path,
        backup_sha256=_sha256(backup_path),
    )


def restore_disaster_backup(batch: ImportBatch) -> DisasterRestoreResult:
    """在显式停机流程中保护当前库后，以同文件系统临时文件原子恢复。"""
    with _confirmation_lock():
        verification = verify_disaster_restore(batch)
        safety_path, safety_hash_path = _backup_current_database(verification.database_path)
        temporary = verification.database_path.with_name(
            f".{verification.database_path.name}.restore.{uuid.uuid4().hex}.tmp"
        )
        replaced = False
        try:
            _copy_and_sync(verification.backup_path, temporary)
            _verify_sqlite_database(temporary, require_batch=batch)
            connections.close_all()
            _ensure_no_sqlite_sidecars(verification.database_path)
            os.replace(temporary, verification.database_path)
            replaced = True
            _verify_sqlite_database(verification.database_path, require_batch=batch)
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            if replaced:
                try:
                    _restore_safety_backup(safety_path, verification.database_path)
                except Exception as rollback_exc:
                    raise DisasterRestoreError(
                        "恢复后的数据库校验失败，且自动回退失败；必须使用恢复前保护备份人工恢复。"
                    ) from rollback_exc
            elif isinstance(exc, DisasterRestoreError):
                raise
            raise DisasterRestoreError(
                "灾难恢复未完成；当前数据库已保持或自动恢复为执行前状态。"
            ) from exc
        return DisasterRestoreResult(
            verification=verification,
            safety_backup_path=safety_path,
            safety_backup_sha256_path=safety_hash_path,
        )


def _configured_database_path() -> Path:
    database = settings.DATABASES["default"]
    if database["ENGINE"] != "django.db.backends.sqlite3":
        raise DisasterRestoreError("灾难恢复命令仅支持SQLite数据库。")
    raw_name = str(database["NAME"])
    if raw_name == ":memory:" or raw_name.startswith("file:"):
        raise DisasterRestoreError("内存SQLite数据库不能执行文件灾难恢复。")
    path = Path(raw_name).expanduser().resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise DisasterRestoreError("当前SQLite数据库不存在或为空。")
    return path


def _bound_backup_path(batch: ImportBatch) -> Path:
    expected = artifact_path(batch.pk, PRE_IMPORT_DATABASE_FILENAME)
    try:
        resolved = expected.resolve(strict=True)
        batch_directory = expected.parent.resolve(strict=True)
    except OSError as exc:
        raise DisasterRestoreError("指定批次的导入前数据库备份不存在。") from exc
    if resolved.parent != batch_directory or resolved.name != PRE_IMPORT_DATABASE_FILENAME:
        raise DisasterRestoreError("数据库备份路径不属于指定批次证据目录。")
    if not resolved.is_file() or resolved.stat().st_size == 0:
        raise DisasterRestoreError("指定批次的数据库备份为空或不是普通文件。")
    return resolved


def _verify_sqlite_database(path: Path, require_batch: ImportBatch | None) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise DisasterRestoreError(f"SQLite文件不存在或为空：{path}")
    database: sqlite3.Connection | None = None
    try:
        database = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        integrity = database.execute("PRAGMA integrity_check").fetchone()
        if integrity != ("ok",):
            raise DisasterRestoreError("SQLite完整性检查失败。")
        tables = {
            row[0]
            for row in database.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        missing = sorted(REQUIRED_TABLES - tables)
        if missing:
            raise DisasterRestoreError(f"SQLite备份缺少关键数据表：{', '.join(missing)}")
        if require_batch is not None:
            row = database.execute(
                "SELECT status, file_hash FROM imports_importbatch WHERE id = ?",
                (require_batch.pk,),
            ).fetchone()
            expected = (ImportStatus.PREVIEWED, require_batch.file_hash)
            if row != expected:
                raise DisasterRestoreError("SQLite备份与指定导入批次不匹配。")
    except (sqlite3.DatabaseError, OSError) as exc:
        raise DisasterRestoreError("SQLite文件无法通过安全校验。") from exc
    finally:
        if database is not None:
            database.close()


def _backup_current_database(database_path: Path) -> tuple[Path, Path]:
    directory = database_path.parent / "disaster_restore_backups"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = timezone.now().strftime("%Y%m%dT%H%M%S%f")
    destination = directory / f"pre_disaster_restore_{stamp}_{uuid.uuid4().hex}.sqlite3"
    hash_path = destination.with_suffix(".sha256")
    temporary = destination.with_name(f".{destination.name}.tmp")
    source: sqlite3.Connection | None = None
    backup: sqlite3.Connection | None = None
    try:
        source = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
        backup = sqlite3.connect(temporary)
        source.backup(backup)
        backup.close()
        backup = None
        source.close()
        source = None
        _verify_sqlite_database(temporary, require_batch=None)
        os.replace(temporary, destination)
        _atomic_write(hash_path, f"{_sha256(destination)}\n".encode("ascii"))
        return destination, hash_path
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        hash_path.unlink(missing_ok=True)
        raise DisasterRestoreError("无法生成恢复前保护备份，未替换当前数据库。") from exc
    finally:
        if backup is not None:
            backup.close()
        if source is not None:
            source.close()


def _copy_and_sync(source: Path, destination: Path) -> None:
    with source.open("rb") as source_file, destination.open("xb") as target_file:
        shutil.copyfileobj(source_file, target_file)
        target_file.flush()
        os.fsync(target_file.fileno())


def _ensure_no_sqlite_sidecars(database_path: Path) -> None:
    sidecars = [
        Path(f"{database_path}-journal"),
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
    ]
    existing = [path.name for path in sidecars if path.exists()]
    if existing:
        raise DisasterRestoreError(
            "检测到SQLite活动或残留边车文件，必须完成干净停机后重试："
            + ", ".join(existing)
        )


def _restore_safety_backup(safety_path: Path, database_path: Path) -> None:
    temporary = database_path.with_name(
        f".{database_path.name}.safety-restore.{uuid.uuid4().hex}.tmp"
    )
    try:
        _copy_and_sync(safety_path, temporary)
        _verify_sqlite_database(temporary, require_batch=None)
        os.replace(temporary, database_path)
        _verify_sqlite_database(database_path, require_batch=None)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as destination:
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
