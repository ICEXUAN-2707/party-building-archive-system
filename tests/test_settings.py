import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

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


class DjangoSettingsProcessTests(SimpleTestCase):
    def test_ci_environment_is_loaded_by_fresh_django_process(self) -> None:
        with TemporaryDirectory() as temp_dir:
            sqlite_path = str(Path(temp_dir) / "ci.sqlite3")
            process_env = os.environ.copy()
            process_env.update(
                {
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
                "'database_name': settings.DATABASES['default']['NAME']"
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
