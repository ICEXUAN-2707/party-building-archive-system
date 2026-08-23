import sys
from unittest.mock import patch

from django.test import SimpleTestCase

from scripts.docker_entrypoint import bounded_int, build_gunicorn_command, main


class DockerEntrypointTests(SimpleTestCase):
    def test_command_keeps_single_worker_and_bounded_defaults(self) -> None:
        command = build_gunicorn_command({})

        self.assertIn("config.wsgi:application", command)
        self.assertIn("--bind=0.0.0.0:8000", command)
        self.assertIn("--workers=1", command)
        self.assertIn("--worker-class=gthread", command)
        self.assertIn("--threads=2", command)
        self.assertIn("--timeout=60", command)
        self.assertNotIn("--access-logfile=-", command)

    def test_command_accepts_reviewed_runtime_tuning(self) -> None:
        command = build_gunicorn_command(
            {
                "GUNICORN_THREADS": "4",
                "GUNICORN_TIMEOUT": "120",
                "GUNICORN_GRACEFUL_TIMEOUT": "45",
            }
        )

        self.assertIn("--threads=4", command)
        self.assertIn("--timeout=120", command)
        self.assertIn("--graceful-timeout=45", command)
        self.assertIn("--workers=1", command)

    def test_bounded_int_rejects_invalid_or_unsafe_values(self) -> None:
        for environment in (
            {"VALUE": "not-a-number"},
            {"VALUE": "0"},
            {"VALUE": "9"},
        ):
            with self.subTest(environment=environment):
                with self.assertRaises(SystemExit):
                    bounded_int(environment, "VALUE", 2, minimum=1, maximum=8)

    @patch("scripts.docker_entrypoint.os.execvp")
    @patch("scripts.docker_entrypoint.subprocess.run")
    def test_main_collects_static_before_replacing_process(self, run, execvp) -> None:
        main()

        run.assert_called_once_with(
            [sys.executable, "manage.py", "collectstatic", "--noinput"],
            check=True,
        )
        command = build_gunicorn_command({})
        execvp.assert_called_once_with("gunicorn", command)
