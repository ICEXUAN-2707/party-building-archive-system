from __future__ import annotations

import hashlib
import os
import re
import shutil
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import BinaryIO

from django.conf import settings

from apps.imports.models import ImportBatch


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ImportEvidenceError(Exception):
    """导入证据缺失、越界或完整性校验失败。"""


class ImportEvidenceNotFound(ImportEvidenceError):
    """导入证据文件不存在。"""


class ImportEvidenceIntegrityError(ImportEvidenceError):
    """导入证据内容与已冻结哈希不一致。"""


@dataclass(frozen=True)
class StoredOriginalFile:
    absolute_path: Path
    relative_name: str
    sha256: str


def sanitize_original_filename(filename: str) -> str:
    """生成仅用于展示/下载的安全文件名，绝不参与服务端路径拼接。"""
    basename = PurePath(str(filename).replace("\\", "/")).name
    cleaned = "".join(
        character
        for character in basename
        if unicodedata.category(character) not in {"Cc", "Cf"}
    ).strip().strip(".")
    if not cleaned:
        return "upload.xlsx"
    return cleaned[:255]


def batch_directory(batch_id: int, *, create: bool = False) -> Path:
    if not isinstance(batch_id, int) or isinstance(batch_id, bool) or batch_id <= 0:
        raise ImportEvidenceIntegrityError("导入批次ID无效。")

    imports_root = (Path(settings.MEDIA_ROOT) / "imports").resolve()
    directory = (imports_root / f"batch_{batch_id}").resolve()
    _ensure_within(directory, imports_root)
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def artifact_path(batch_id: int, filename: str) -> Path:
    if not filename or PurePath(filename).name != filename:
        raise ImportEvidenceIntegrityError("导入证据文件名无效。")
    directory = batch_directory(batch_id)
    target = (directory / filename).resolve()
    _ensure_within(target, directory)
    return target


def store_uploaded_file(batch: ImportBatch, uploaded_file) -> StoredOriginalFile:
    directory = batch_directory(batch.pk, create=True)
    filename = f"original_{uuid.uuid4().hex}.xlsx"
    final_path = artifact_path(batch.pk, filename)
    temporary_name = f"imports/batch_{batch.pk}/.{filename}.{uuid.uuid4().hex}.tmp"
    storage = batch.stored_file.storage
    stored_temporary_name: str | None = None
    digest = hashlib.sha256()

    try:
        # 经FileField配置的Django存储后端落盘，再在同目录完成原子替换。
        stored_temporary_name = storage.save(temporary_name, uploaded_file)
        temporary_path = Path(storage.path(stored_temporary_name)).resolve()
        _ensure_within(temporary_path, directory)
        with temporary_path.open("r+b") as persisted:
            persisted.flush()
            os.fsync(persisted.fileno())
            persisted.seek(0)
            for chunk in iter(lambda: persisted.read(1024 * 1024), b""):
                digest.update(chunk)
        os.replace(temporary_path, final_path)
    except Exception:
        if stored_temporary_name is not None:
            storage.delete(stored_temporary_name)
        final_path.unlink(missing_ok=True)
        raise

    media_root = Path(settings.MEDIA_ROOT).resolve()
    relative_name = final_path.relative_to(media_root).as_posix()
    return StoredOriginalFile(
        absolute_path=final_path,
        relative_name=relative_name,
        sha256=digest.hexdigest(),
    )


def verified_original_path(batch: ImportBatch) -> Path:
    expected_directory = batch_directory(batch.pk)
    stored_name = str(batch.stored_file.name or "")
    if not stored_name:
        raise ImportEvidenceNotFound("原始Excel文件不存在。")

    media_root = Path(settings.MEDIA_ROOT).resolve()
    candidate = (media_root / PurePath(stored_name)).resolve()
    _ensure_within(candidate, expected_directory)
    if not candidate.is_file():
        raise ImportEvidenceNotFound("原始Excel文件不存在。")
    if not _SHA256_PATTERN.fullmatch(batch.file_hash or ""):
        raise ImportEvidenceIntegrityError("原始Excel哈希格式无效。")

    actual_hash = sha256_file(candidate)
    if actual_hash != batch.file_hash:
        raise ImportEvidenceIntegrityError("原始Excel完整性校验失败。")
    return candidate


def open_verified_original(batch: ImportBatch) -> BinaryIO:
    source = verified_original_path(batch).open("rb")
    digest = hashlib.sha256()
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(chunk)
    if digest.hexdigest() != batch.file_hash:
        source.close()
        raise ImportEvidenceIntegrityError("原始Excel完整性校验失败。")
    source.seek(0)
    return source


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remove_batch_directory(batch_id: int) -> None:
    directory = batch_directory(batch_id)
    if directory.exists():
        shutil.rmtree(directory)


def _ensure_within(path: Path, parent: Path) -> None:
    try:
        path.relative_to(parent)
    except ValueError as exc:
        raise ImportEvidenceIntegrityError("导入证据路径越界。") from exc
