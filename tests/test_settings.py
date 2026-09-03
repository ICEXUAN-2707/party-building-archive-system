import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config import settings as project_settings


class EnvironmentHelperTests(SimpleTestCase):
    def test_os_environment_has_priority_over_dotenv(self) -> None:
        with (
            patch.dict(project_settings._ENV_FILE_VALUES, {"EXAMPLE_SETTING": "from-dotenv"}, clear=True),
            patch.dict(os.environ, {"EXAMPLE_SETTING": "from-os"}, clear=False),
        ):
            self.assertEqual(project_settings.env("EXAMPLE_SETTING"), "from-os")

    def test_dotenv_is_used_when_os_environment_is_missing(self) -> None:
        with (
            patch.dict(project_settings._ENV_FILE_VALUES, {"EXAMPLE_SETTING": "from-dotenv"}, clear=True),
            patch.dict(os.environ, {}, clear=False),
        ):
            os.environ.pop("EXAMPLE_SETTING", None)
            self.assertEqual(project_settings.env("EXAMPLE_SETTING"), "from-dotenv")

    def test_default_is_used_when_other_sources_are_missing(self) -> None:
        with (
            patch.dict(project_settings._ENV_FILE_VALUES, {}, clear=True),
            patch.dict(os.environ, {}, clear=False),
        ):
            os.environ.pop("EXAMPLE_SETTING", None)
            self.assertEqual(project_settings.env("EXAMPLE_SETTING", "fallback"), "fallback")

    def test_load_dotenv_keeps_local_development_support(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "\n".join(
                    (
                        "# 本地开发配置",
                        "DJANGO_DEBUG=False",
                        'DJANGO_SECRET_KEY="local-secret"',
                        "INVALID_LINE",
                    )
                ),
                encoding="utf-8",
            )

            values = project_settings.load_dotenv(env_file)

        self.assertEqual(values["DJANGO_DEBUG"], "False")
        self.assertEqual(values["DJANGO_SECRET_KEY"], "local-secret")
        self.assertNotIn("INVALID_LINE", values)

    def test_bool_and_list_helpers_use_normalized_values(self) -> None:
        with (
            patch.dict(project_settings._ENV_FILE_VALUES, {}, clear=True),
            patch.dict(
                os.environ,
                {
                    "EXAMPLE_BOOL": "YES",
                    "EXAMPLE_LIST": "localhost, testserver, ,127.0.0.1",
                },
                clear=False,
            ),
        ):
            self.assertIs(project_settings.env_bool("EXAMPLE_BOOL"), True)
            self.assertEqual(
                project_settings.env_list("EXAMPLE_LIST"),
                ["localhost", "testserver", "127.0.0.1"],
            )

    def test_bool_helper_rejects_unknown_value(self) -> None:
        with (
            patch.dict(project_settings._ENV_FILE_VALUES, {}, clear=True),
            patch.dict(os.environ, {"EXAMPLE_BOOL": "truthy"}, clear=False),
        ):
            with self.assertRaisesMessage(ImproperlyConfigured, "EXAMPLE_BOOL必须是布尔值"):
                project_settings.env_bool("EXAMPLE_BOOL")


class DjangoSettingsProcessTests(SimpleTestCase):
    def test_ci_environment_is_loaded_by_fresh_django_process(self) -> None:
        with TemporaryDirectory() as temp_dir:
            sqlite_path = str(Path(temp_dir) / "ci.sqlite3")
            process_env = os.environ.copy()
            process_env.update(
                {
                    "PYTHONUTF8": "1",
                    "DJANGO_SECRET_KEY": "ci-only-test-secret",
                    "DJANGO_DEBUG": "False",
                    "DJANGO_ALLOWED_HOSTS": "127.0.0.1,localhost,testserver",
                    "DJANGO_SQLITE_PATH": sqlite_path,
                }
            )
            command = (
                "import json; "
                "from config import settings; "
                "print(json.dumps({"
                "'secret_key': settings.SECRET_KEY, "
                "'debug': settings.DEBUG, "
                "'allowed_hosts': settings.ALLOWED_HOSTS, "
                "'database_name': str(settings.DATABASES['default']['NAME'])"
                "}))"
            )

            completed = subprocess.run(
                [sys.executable, "-c", command],
                cwd=project_settings.BASE_DIR,
                env=process_env,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            loaded = json.loads(completed.stdout)

        self.assertEqual(loaded["secret_key"], "ci-only-test-secret")
        self.assertIs(loaded["debug"], False)
        self.assertEqual(
            loaded["allowed_hosts"],
            ["127.0.0.1", "localhost", "testserver"],
        )
        self.assertEqual(Path(loaded["database_name"]), Path(sqlite_path))

    def test_production_rejects_development_defaults(self) -> None:
        process_env = os.environ.copy()
        for name in (
            "DJANGO_SECRET_KEY",
            "DJANGO_ALLOWED_HOSTS",
            "DJANGO_CSRF_TRUSTED_ORIGINS",
            "DJANGO_SQLITE_PATH",
            "DJANGO_MEDIA_ROOT",
            "DJANGO_STATIC_ROOT",
            "DJANGO_BACKUP_ROOT",
        ):
            process_env.pop(name, None)
        process_env.update(
            {
                "PYTHONUTF8": "1",
                "DJANGO_PRODUCTION": "True",
                "DJANGO_DEBUG": "False",
            }
        )

        completed = subprocess.run(
            [sys.executable, "-c", "from config import settings"],
            cwd=project_settings.BASE_DIR,
            env=process_env,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("生产配置无效", completed.stderr)
        self.assertNotIn("dev-only-change-me", completed.stderr)

    def test_production_loads_http_ipv4_and_persistent_paths(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            process_env = os.environ.copy()
            process_env.update(
                {
                    "PYTHONUTF8": "1",
                    "DJANGO_PRODUCTION": "True",
                    "DJANGO_SECRET_KEY": "prod-test-A7!x9#secure-key-with-varied-characters-2026-08-23",
                    "DJANGO_DEBUG": "False",
                    "DJANGO_ALLOWED_HOSTS": "8.8.8.8",
                    "DJANGO_CSRF_TRUSTED_ORIGINS": "http://8.8.8.8",
                    "DJANGO_SQLITE_PATH": str(root / "database" / "db.sqlite3"),
                    "DJANGO_MEDIA_ROOT": str(root / "media"),
                    "DJANGO_STATIC_ROOT": str(root / "static"),
                    "DJANGO_BACKUP_ROOT": str(root / "backups"),
                    "DJANGO_LOG_LEVEL": "info",
                }
            )
            command = (
                "import json; from config import settings; "
                "print(json.dumps({"
                "'production': settings.PRODUCTION, "
                "'debug': settings.DEBUG, "
                "'ssl_redirect': settings.SECURE_SSL_REDIRECT, "
                "'session_secure': settings.SESSION_COOKIE_SECURE, "
                "'csrf_secure': settings.CSRF_COOKIE_SECURE, "
                "'hsts_seconds': settings.SECURE_HSTS_SECONDS, "
                "'media_root': str(settings.MEDIA_ROOT), "
                "'static_root': str(settings.STATIC_ROOT), "
                "'backup_root': str(settings.BACKUP_ROOT), "
                "'log_level': settings.LOG_LEVEL"
                "}))"
            )

            completed = subprocess.run(
                [sys.executable, "-c", command],
                cwd=project_settings.BASE_DIR,
                env=process_env,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            loaded = json.loads(completed.stdout)

        self.assertIs(loaded["production"], True)
        self.assertIs(loaded["debug"], False)
        self.assertIs(loaded["ssl_redirect"], False)
        self.assertIs(loaded["session_secure"], False)
        self.assertIs(loaded["csrf_secure"], False)
        self.assertEqual(loaded["hsts_seconds"], 0)
        self.assertEqual(Path(loaded["media_root"]), root / "media")
        self.assertEqual(Path(loaded["static_root"]), root / "static")
        self.assertEqual(Path(loaded["backup_root"]), root / "backups")
        self.assertEqual(loaded["log_level"], "INFO")

    def test_production_rejects_non_public_ipv4_or_mismatched_origin(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            required = {
                "PYTHONUTF8": "1",
                "DJANGO_PRODUCTION": "True",
                "DJANGO_SECRET_KEY": "prod-test-A7!x9#secure-key-with-varied-characters-2026-08-23",
                "DJANGO_DEBUG": "False",
                "DJANGO_SQLITE_PATH": str(root / "database" / "db.sqlite3"),
                "DJANGO_MEDIA_ROOT": str(root / "media"),
                "DJANGO_STATIC_ROOT": str(root / "static"),
                "DJANGO_BACKUP_ROOT": str(root / "backups"),
            }
            invalid_pairs = (
                ("party.example.edu.cn", "http://party.example.edu.cn"),
                ("192.168.1.10", "http://192.168.1.10"),
                ("8.8.8.8", "https://8.8.8.8"),
                ("8.8.8.8,1.1.1.1", "http://8.8.8.8"),
            )
            for host, origin in invalid_pairs:
                with self.subTest(host=host, origin=origin):
                    process_env = os.environ.copy()
                    process_env.update(required)
                    process_env.update(
                        {
                            "DJANGO_ALLOWED_HOSTS": host,
                            "DJANGO_CSRF_TRUSTED_ORIGINS": origin,
                        }
                    )
                    completed = subprocess.run(
                        [sys.executable, "-c", "from config import settings"],
                        cwd=project_settings.BASE_DIR,
                        env=process_env,
                        check=False,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                    )
                    self.assertNotEqual(completed.returncode, 0)

    def test_production_rejects_relative_persistence_paths(self) -> None:
        process_env = os.environ.copy()
        process_env.update(
            {
                "PYTHONUTF8": "1",
                "DJANGO_PRODUCTION": "True",
                "DJANGO_SECRET_KEY": "prod-test-A7!x9#secure-key-with-varied-characters-2026-08-23",
                "DJANGO_DEBUG": "False",
                "DJANGO_ALLOWED_HOSTS": "8.8.8.8",
                "DJANGO_CSRF_TRUSTED_ORIGINS": "http://8.8.8.8",
                "DJANGO_SQLITE_PATH": "data/db.sqlite3",
                "DJANGO_MEDIA_ROOT": "data/media",
                "DJANGO_STATIC_ROOT": "data/static",
                "DJANGO_BACKUP_ROOT": "data/backups",
            }
        )

        completed = subprocess.run(
            [sys.executable, "-c", "from config import settings"],
            cwd=project_settings.BASE_DIR,
            env=process_env,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("生产环境必须是绝对路径", completed.stderr)
