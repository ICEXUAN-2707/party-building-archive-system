from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from scripts.ci_guard import (
    CI_SQLITE_ARTIFACT_NAMES,
    find_absolute_paths,
    find_ci_temp_database_artifacts,
    find_forbidden_tracked_files,
    find_missing_required_files,
    find_post_test_artifacts,
)


class RequiredFileGuardTests(SimpleTestCase):
    def test_missing_required_file_is_reported(self) -> None:
        with TemporaryDirectory() as temp_dir:
            problems = find_missing_required_files(
                Path(temp_dir),
                ("manage.py", "requirements.txt"),
            )

        self.assertEqual(
            {problem.path for problem in problems},
            {"manage.py", "requirements.txt"},
        )

    def test_existing_required_file_passes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "manage.py").touch()
            problems = find_missing_required_files(root, ("manage.py",))

        self.assertEqual(problems, [])


class ForbiddenTrackedFileGuardTests(SimpleTestCase):
    def test_sensitive_and_generated_files_are_reported(self) -> None:
        problems = find_forbidden_tracked_files(
            (
                ".env",
                "db.sqlite3",
                "data/students.xlsx",
                "apps/__pycache__/views.pyc",
                ".venv/pyvenv.cfg",
                "media/imports/upload.xlsx",
            )
        )

        self.assertEqual(len(problems), 6)

    def test_expected_repository_placeholders_are_allowed(self) -> None:
        problems = find_forbidden_tracked_files(
            (
                ".env.example",
                "media/imports/.gitkeep",
                "apps/imports/migrations/0001_initial.py",
            )
        )

        self.assertEqual(problems, [])


class AbsolutePathGuardTests(SimpleTestCase):
    def test_developer_absolute_path_is_reported_with_line_number(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs_dir = root / "docs"
            docs_dir.mkdir()
            note = docs_dir / "note.md"
            note.write_text(
                "relative/path\nC:\\Users\\Developer\\project\\file.py\n",  # ci-guard: allow-absolute-path
                encoding="utf-8",
            )

            problems = find_absolute_paths(root, ("docs/note.md",))

        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0].line_number, 2)

    def test_relative_paths_pass(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir()
            script = scripts_dir / "example.py"
            script.write_text("path = 'docs/spec.md'\n", encoding="utf-8")

            problems = find_absolute_paths(root, ("scripts/example.py",))

        self.assertEqual(problems, [])

    def test_http_urls_are_not_treated_as_windows_drive_paths(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs_dir = root / "docs"
            docs_dir.mkdir()
            note = docs_dir / "links.md"
            note.write_text(
                "http://127.0.0.1:8000/\n"
                "https://cdn.jsdelivr.net/npm/bootstrap@5/dist/bootstrap.min.css\n",
                encoding="utf-8",
            )

            problems = find_absolute_paths(root, ("docs/links.md",))

        self.assertEqual(problems, [])


class PostTestArtifactGuardTests(SimpleTestCase):
    def test_database_excel_upload_and_backup_artifacts_are_reported(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "db.sqlite3").touch()
            (root / "temporary.xlsx").touch()
            (root / "database.backup").touch()
            upload_dir = root / "media" / "imports"
            upload_dir.mkdir(parents=True)
            (upload_dir / "test-upload.bin").touch()

            problems = find_post_test_artifacts(root)

        self.assertEqual(
            {problem.path for problem in problems},
            {
                "database.backup",
                "db.sqlite3",
                "media/imports/test-upload.bin",
                "temporary.xlsx",
            },
        )

    def test_ignored_virtual_environment_and_gitkeep_pass(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            venv_dir = root / ".venv"
            venv_dir.mkdir()
            (venv_dir / "cached.xlsx").touch()
            upload_dir = root / "media" / "imports"
            upload_dir.mkdir(parents=True)
            (upload_dir / ".gitkeep").touch()

            problems = find_post_test_artifacts(root)

        self.assertEqual(problems, [])


class CiTempDatabaseArtifactGuardTests(SimpleTestCase):
    def test_ci_database_and_sidecar_artifacts_are_reported(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected_names = {
                "ci.sqlite3",
                "ci.sqlite3-wal",
                "test_ci.sqlite3",
                "test_ci.sqlite3-journal",
            }
            for artifact_name in expected_names:
                (root / artifact_name).touch()

            problems = find_ci_temp_database_artifacts(root)

        self.assertEqual(
            {Path(problem.path).name for problem in problems},
            expected_names,
        )

    def test_unrelated_sqlite_files_are_not_in_cleanup_scope(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "production.sqlite3").touch()

            problems = find_ci_temp_database_artifacts(root)

        self.assertEqual(problems, [])

    def test_clean_temp_directory_passes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            problems = find_ci_temp_database_artifacts(Path(temp_dir))

        self.assertEqual(problems, [])

    def test_cleanup_scope_contains_only_fixed_filenames(self) -> None:
        self.assertEqual(len(CI_SQLITE_ARTIFACT_NAMES), 8)
        self.assertEqual(len(set(CI_SQLITE_ARTIFACT_NAMES)), 8)
        self.assertTrue(
            all(Path(name).name == name for name in CI_SQLITE_ARTIFACT_NAMES)
        )
