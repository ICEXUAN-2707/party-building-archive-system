from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from scripts.run_deployment_load_test import run_load_test


class DeploymentLoadTestRunnerTests(SimpleTestCase):
    def test_rejects_dataset_smaller_than_release_gate(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                run_load_test(Path(temp_dir), student_count=499, seed=1)

    @patch("scripts.run_deployment_load_test.subprocess.run")
    @patch("scripts.run_deployment_load_test.run_acceptance")
    def test_writes_pass_report_without_lock_or_5xx(self, acceptance, run) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            acceptance_report = root / "acceptance.json"
            acceptance_report.write_text(
                '{"git_sha":"abc123","timings":{"total_seconds":1.25}}',
                encoding="utf-8",
            )
            acceptance.return_value = acceptance_report
            run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            report_path = run_load_test(root, student_count=500, seed=7)

            report = report_path.read_text(encoding="utf-8")
            self.assertIn('"result": "passed"', report)
            self.assertIn('"database_locked_errors": 0', report)
            self.assertIn('"http_5xx_errors": 0', report)
