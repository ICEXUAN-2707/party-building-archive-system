from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from scripts.container_smoke_test import (
    SmokeFailure,
    assert_branches,
    compose_command,
    require_ci_workspace,
    write_runtime_files,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "container-ci.yml"


class ContainerWorkflowContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_has_required_triggers_and_read_only_permissions(self) -> None:
        self.assertIn("pull_request:", self.workflow)
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn("contents: read", self.workflow)
        self.assertIn("cancel-in-progress: true", self.workflow)

    def test_workflow_builds_scans_and_smokes_candidate_sha(self) -> None:
        self.assertIn("party-archive-web:${{ github.sha }}", self.workflow)
        self.assertIn("docker build --pull", self.workflow)
        self.assertIn("scripts/container_smoke_test.py", self.workflow)
        self.assertIn("severity: CRITICAL", self.workflow)

    def test_workflow_runs_complete_application_gates(self) -> None:
        self.assertIn("python manage.py check", self.workflow)
        self.assertIn("python manage.py makemigrations --check", self.workflow)
        self.assertIn("Run complete Django test suite", self.workflow)
        self.assertIn("run: python manage.py test", self.workflow)

    def test_all_actions_are_pinned_to_full_commit_sha(self) -> None:
        action_lines = [line.strip() for line in self.workflow.splitlines() if "uses:" in line]
        self.assertGreaterEqual(len(action_lines), 3)
        for line in action_lines:
            reference = line.split("@", 1)[1].split()[0]
            self.assertRegex(reference, r"^[0-9a-f]{40}$")


class ContainerSmokeSafetyTests(SimpleTestCase):
    def test_workspace_must_be_inside_runner_temp(self) -> None:
        with TemporaryDirectory() as temp_dir:
            runner_temp = Path(temp_dir)
            child = runner_temp / "smoke"
            resolved = require_ci_workspace(
                child,
                {"GITHUB_ACTIONS": "true", "RUNNER_TEMP": str(runner_temp)},
            )
            self.assertEqual(resolved, child.resolve())

            with self.assertRaises(SmokeFailure):
                require_ci_workspace(
                    runner_temp.parent / "outside",
                    {"GITHUB_ACTIONS": "true", "RUNNER_TEMP": str(runner_temp)},
                )

    def test_workspace_rejects_non_ci_execution(self) -> None:
        with self.assertRaises(SmokeFailure):
            require_ci_workspace(Path("smoke"), {})

    def test_runtime_files_use_only_ci_values_and_loopback_ports(self) -> None:
        with TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            production_env, compose_env = write_runtime_files(
                workspace, "party-archive-web:test-sha", "party-archive-test"
            )
            production = production_env.read_text(encoding="utf-8")
            compose = compose_env.read_text(encoding="utf-8")

        self.assertIn("DJANGO_PRODUCTION=True", production)
        self.assertIn("DJANGO_ALLOWED_HOSTS=8.8.8.8", production)
        self.assertIn("DJANGO_CSRF_TRUSTED_ORIGINS=http://8.8.8.8", production)
        self.assertIn("WEB_IMAGE=party-archive-web:test-sha", compose)
        self.assertIn(f"PARTY_ARCHIVE_ROOT={workspace.as_posix()}", compose)
        self.assertNotIn(f"PARTY_ARCHIVE_ROOT={(workspace / 'data').as_posix()}", compose)
        self.assertIn("HTTP_BIND_ADDRESS=127.0.0.1", compose)
        self.assertNotIn("HTTPS_BIND_ADDRESS", compose)

    def test_compose_cleanup_never_requests_volume_deletion(self) -> None:
        command = compose_command(Path("compose.env"), "down", "--remove-orphans")
        self.assertNotIn("--volumes", command)
        self.assertNotIn("-v", command)

    @patch("scripts.container_smoke_test.run")
    def test_branch_count_ignores_django_shell_auto_import_notice(self, mocked_run) -> None:
        mocked_run.return_value.stdout = (
            "15 objects imported automatically (use -v 2 for details).\n\n"
            "PARTY_BRANCH_COUNT=9\n"
        )

        assert_branches("party-archive-web:test", Path("production.env"), Path("smoke"))

    @patch("scripts.container_smoke_test.subprocess.run")
    def test_command_runner_never_uses_shell(self, mocked_run) -> None:
        from scripts.container_smoke_test import run

        run(["docker", "version"])

        _, kwargs = mocked_run.call_args
        self.assertNotIn("shell", kwargs)
