from pathlib import Path

from django.test import SimpleTestCase

from config.settings import BASE_DIR


class DockerImageContractTests(SimpleTestCase):
    def test_dockerfile_uses_pinned_python_and_non_root_runtime(self) -> None:
        dockerfile = (BASE_DIR / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("FROM python:3.12.14-slim-bookworm", dockerfile)
        self.assertIn("USER app", dockerfile)
        self.assertIn('ENTRYPOINT ["python", "/app/scripts/docker_entrypoint.py"]', dockerfile)
        self.assertNotIn("runserver", dockerfile)
        self.assertNotIn("COPY . ", dockerfile)

    def test_dockerignore_excludes_secrets_and_business_data(self) -> None:
        ignored = {
            line.strip()
            for line in (BASE_DIR / ".dockerignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }

        required = {
            ".env",
            "*.sqlite3",
            "*.xlsx",
            "media",
            "backups",
            "disaster_restore_backups",
            ".venv",
            ".git",
        }
        self.assertTrue(required.issubset(ignored))

    def test_entrypoint_is_included_by_explicit_image_copy(self) -> None:
        dockerfile = (BASE_DIR / "Dockerfile").read_text(encoding="utf-8")
        entrypoint = Path(BASE_DIR / "scripts" / "docker_entrypoint.py")

        self.assertTrue(entrypoint.is_file())
        self.assertIn(
            "COPY --chown=app:app scripts/__init__.py scripts/docker_entrypoint.py ./scripts/",
            dockerfile,
        )
