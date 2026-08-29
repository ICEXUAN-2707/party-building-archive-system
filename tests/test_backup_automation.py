from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.imports.backup_service import BackupError, create_full_backup, verify_full_backup
from apps.imports.cos_backup import CosBackupError, download_versioned_backup, upload_verified_backup


class BackupArchiveTests(TestCase):
    def test_backup_contains_verified_database_and_media_manifest(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root / "media"
            backups = root / "backups"
            evidence = media / "imports/batch_1/original.xlsx"
            evidence.parent.mkdir(parents=True)
            evidence.write_bytes(b"synthetic-only")
            with override_settings(MEDIA_ROOT=media, BACKUP_ROOT=backups):
                result = create_full_backup(now=datetime(2026, 8, 29, tzinfo=timezone.utc))
                manifest = verify_full_backup(result.archive_path)

            self.assertEqual(manifest["schema_version"], 1)
            self.assertEqual(manifest["reason"], "daily")
            self.assertEqual(manifest["media_files"][0]["path"], "imports/batch_1/original.xlsx")
            self.assertEqual(len(result.sha256), 64)

    def test_tampered_archive_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            with override_settings(MEDIA_ROOT=root / "media", BACKUP_ROOT=root / "backups"):
                result = create_full_backup(now=datetime(2026, 8, 29, tzinfo=timezone.utc))
                result.archive_path.write_bytes(result.archive_path.read_bytes() + b"tamper")
                with self.assertRaisesRegex(BackupError, "SHA-256"):
                    verify_full_backup(result.archive_path)


class FakeCosClient:
    def __init__(self, *, encrypted: bool = True, versioned: bool = True) -> None:
        self.payload = b""
        self.metadata: dict[str, str] = {}
        self.encrypted = encrypted
        self.versioned = versioned

    def put_object(self, **kwargs: object) -> dict[str, str]:
        self.payload = kwargs["Body"].read()
        self.metadata = kwargs["Metadata"]
        self.server_side_encryption = kwargs["ServerSideEncryption"]
        return {"x-cos-version-id": "version-1"} if self.versioned else {}

    def head_object(self, **kwargs: object) -> dict[str, object]:
        response: dict[str, object] = {
            "Content-Length": len(self.payload),
            "x-cos-meta-sha256": self.metadata["sha256"],
        }
        if self.encrypted:
            response["x-cos-server-side-encryption"] = "AES256"
        return response

    def get_object(self, **kwargs: object) -> dict[str, object]:
        payload = self.payload

        class Body:
            def get_stream_to_file(self, destination: str) -> None:
                Path(destination).write_bytes(payload)

        return {"Body": Body()}


class CosBackupTests(TestCase):
    def test_upload_requires_sse_cos_metadata_and_version_id(self) -> None:
        with TemporaryDirectory() as temporary:
            archive = Path(temporary) / "backup.tar.gz"
            archive.write_bytes(b"verified backup")
            client = FakeCosClient()
            with patch.dict(os.environ, {"COS_BACKUP_BUCKET": "private-123", "COS_BACKUP_REGION": "ap-beijing"}, clear=False):
                result = upload_verified_backup(archive, client=client)

            self.assertEqual(client.server_side_encryption, "AES256")
            self.assertEqual(result.version_id, "version-1")
            self.assertEqual(client.metadata["sha256"], result.sha256)

    def test_upload_rejects_unencrypted_or_unversioned_object(self) -> None:
        with TemporaryDirectory() as temporary:
            archive = Path(temporary) / "backup.tar.gz"
            archive.write_bytes(b"verified backup")
            environment = {"COS_BACKUP_BUCKET": "private-123", "COS_BACKUP_REGION": "ap-beijing"}
            with patch.dict(os.environ, environment, clear=False):
                with self.assertRaises(CosBackupError):
                    upload_verified_backup(archive, client=FakeCosClient(encrypted=False))
                with self.assertRaises(CosBackupError):
                    upload_verified_backup(archive, client=FakeCosClient(versioned=False))

    def test_versioned_download_verifies_sha_before_publishing_file(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.tar.gz"
            source.write_bytes(b"versioned backup")
            client = FakeCosClient()
            environment = {"COS_BACKUP_BUCKET": "private-123", "COS_BACKUP_REGION": "ap-beijing"}
            with patch.dict(os.environ, environment, clear=False):
                upload_verified_backup(source, client=client)
                destination = root / "restored.tar.gz"
                download_versioned_backup("prefix/source.tar.gz", "version-1", destination, client=client)

            self.assertEqual(destination.read_bytes(), source.read_bytes())
            self.assertTrue((root / "restored.sha256").is_file())
