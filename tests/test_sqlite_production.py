from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.audit.sqlite_pragmas import configure_sqlite_connection
from scripts.docker_entrypoint import build_gunicorn_command


class SQLiteProductionConfigurationTests(SimpleTestCase):
    @patch("apps.audit.sqlite_pragmas.settings.PRODUCTION", True)
    @patch.dict(
        "apps.audit.sqlite_pragmas.settings.DATABASES",
        {"default": {"OPTIONS": {"timeout": 30.0}}},
        clear=True,
    )
    def test_new_production_connection_enables_wal_and_busy_timeout(self) -> None:
        cursor = MagicMock()
        connection = SimpleNamespace(
            vendor="sqlite",
            alias="default",
            cursor=MagicMock(return_value=cursor),
        )
        cursor.__enter__.return_value = cursor

        configure_sqlite_connection(sender=None, connection=connection)

        self.assertEqual(
            [call.args[0] for call in cursor.execute.call_args_list],
            [
                "PRAGMA journal_mode=WAL",
                "PRAGMA busy_timeout=30000",
                "PRAGMA synchronous=NORMAL",
            ],
        )

    def test_runtime_defaults_to_two_workers(self) -> None:
        self.assertIn("--workers=2", build_gunicorn_command({}))
