from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from scripts.ci_database_cleanup import (
    clean_ci_database_artifacts,
    main,
    validate_ci_database_path,
)
from scripts.ci_guard import CI_SQLITE_ARTIFACT_NAMES


class CiDatabaseCleanupTests(SimpleTestCase):
    def test_all_fixed_database_artifacts_are_removed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            runner_temp = Path(temp_dir)
            database_path = runner_temp / "ci.sqlite3"
            for artifact_name in CI_SQLITE_ARTIFACT_NAMES:
                (runner_temp / artifact_name).touch()

            clean_ci_database_artifacts(runner_temp, database_path)

            self.assertFalse(
                any((runner_temp / name).exists() for name in CI_SQLITE_ARTIFACT_NAMES)
            )

    def test_unrelated_database_is_preserved(self) -> None:
        with TemporaryDirectory() as temp_dir:
            runner_temp = Path(temp_dir)
            unrelated_database = runner_temp / "production.sqlite3"
            unrelated_database.touch()

            clean_ci_database_artifacts(runner_temp, runner_temp / "ci.sqlite3")

            self.assertTrue(unrelated_database.exists())

    def test_database_outside_runner_temp_is_rejected(self) -> None:
        with TemporaryDirectory() as temp_dir, TemporaryDirectory() as other_dir:
            with self.assertRaisesRegex(ValueError, "outside RUNNER_TEMP"):
                validate_ci_database_path(
                    Path(temp_dir),
                    Path(other_dir) / "ci.sqlite3",
                )

    def test_unexpected_database_name_is_rejected(self) -> None:
        with TemporaryDirectory() as temp_dir:
            runner_temp = Path(temp_dir)
            with self.assertRaisesRegex(ValueError, "outside RUNNER_TEMP"):
                validate_ci_database_path(
                    runner_temp,
                    runner_temp / "production.sqlite3",
                )

    def test_missing_environment_is_reported(self) -> None:
        with redirect_stderr(StringIO()):
            result = main({})

        self.assertEqual(result, 1)
