from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path


class CosBackupError(RuntimeError):
    pass


@dataclass(frozen=True)
class CosUploadResult:
    object_key: str
    version_id: str
    sha256: str


def download_versioned_backup(
    object_key: str, version_id: str, destination: Path, *, client: object | None = None
) -> Path:
    bucket = _required("COS_BACKUP_BUCKET")
    region = _required("COS_BACKUP_REGION")
    client = client or _create_client(region)
    metadata = client.head_object(Bucket=bucket, Key=object_key, VersionId=version_id)
    expected_sha256 = metadata.get("x-cos-meta-sha256")
    if metadata.get("x-cos-server-side-encryption") != "AES256" or not expected_sha256:
        raise CosBackupError("COS恢复源缺少SSE-COS或SHA-256元数据。")
    response = client.get_object(Bucket=bucket, Key=object_key, VersionId=version_id)
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.download-{os.getpid()}")
    try:
        response["Body"].get_stream_to_file(str(temporary))
        if _sha256(temporary) != expected_sha256:
            raise CosBackupError("COS下载归档SHA-256校验失败。")
        os.replace(temporary, destination)
        destination.with_suffix("").with_suffix(".sha256").write_text(
            f"{expected_sha256}  {destination.name}\n", encoding="ascii"
        )
    finally:
        if temporary.exists():
            temporary.unlink()
    return destination


def upload_verified_backup(archive_path: Path, *, client: object | None = None) -> CosUploadResult:
    archive_path = archive_path.resolve()
    sha256 = _sha256(archive_path)
    bucket = _required("COS_BACKUP_BUCKET")
    region = _required("COS_BACKUP_REGION")
    prefix = os.environ.get("COS_BACKUP_PREFIX", "party-archive").strip("/")
    object_key = f"{prefix}/{archive_path.name}"
    client = client or _create_client(region)
    with archive_path.open("rb") as source:
        response = client.put_object(
            Bucket=bucket,
            Body=source,
            Key=object_key,
            ServerSideEncryption="AES256",
            Metadata={"sha256": sha256},
        )
    metadata = client.head_object(Bucket=bucket, Key=object_key)
    encryption = metadata.get("x-cos-server-side-encryption")
    remote_sha256 = metadata.get("x-cos-meta-sha256")
    size = int(metadata.get("Content-Length", metadata.get("content-length", -1)))
    version_id = response.get("x-cos-version-id") or metadata.get("x-cos-version-id")
    if encryption != "AES256" or remote_sha256 != sha256 or size != archive_path.stat().st_size:
        raise CosBackupError("COS对象加密或完整性元数据验证失败。")
    if not version_id:
        raise CosBackupError("COS未返回版本ID；请确认存储桶已启用版本控制。")
    return CosUploadResult(object_key, str(version_id), sha256)


def _create_client(region: str) -> object:
    try:
        from qcloud_cos import CosConfig, CosS3Client
    except ImportError as exc:
        raise CosBackupError("缺少cos-python-sdk-v5。") from exc
    config = CosConfig(
        Region=region,
        SecretId=_required("COS_SECRET_ID"),
        SecretKey=_required("COS_SECRET_KEY"),
        Token=os.environ.get("COS_SESSION_TOKEN"),
        Scheme="https",
    )
    return CosS3Client(config)


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise CosBackupError(f"缺少{name}。")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
