"""Run the production Compose smoke test in an isolated GitHub Actions directory."""

from __future__ import annotations

import argparse
import http.client
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = PROJECT_ROOT / "compose.production.yml"
APP_UID_GID = "10001:10001"
SMOKE_HOST = "8.8.8.8"


class SmokeFailure(RuntimeError):
    """A release-blocking container smoke failure."""


def run(
    command: Sequence[str],
    *,
    check: bool = True,
    capture_output: bool = False,
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=PROJECT_ROOT,
        check=check,
        capture_output=capture_output,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )


def require_ci_workspace(workspace: Path, environment: dict[str, str]) -> Path:
    if environment.get("GITHUB_ACTIONS", "").lower() != "true":
        raise SmokeFailure("container smoke test may only run in GitHub Actions")
    runner_temp_raw = environment.get("RUNNER_TEMP")
    if not runner_temp_raw:
        raise SmokeFailure("RUNNER_TEMP is required")
    runner_temp = Path(runner_temp_raw).resolve()
    resolved = workspace.resolve()
    if resolved == runner_temp or runner_temp not in resolved.parents:
        raise SmokeFailure("workspace must be a child of RUNNER_TEMP")
    return resolved


def write_runtime_files(workspace: Path, image: str, project_name: str) -> tuple[Path, Path]:
    data_root = workspace / "data"
    for name in ("database", "media", "static", "backups"):
        (data_root / name).mkdir(parents=True, exist_ok=True)

    production_env = workspace / ".env.production"
    production_env.write_text(
        "\n".join(
            (
                "DJANGO_PRODUCTION=True",
                "DJANGO_SECRET_KEY=ci-container-smoke-only-7Vx9Qm2Lp4Nk6Rt8Yw3Hs5Df1Za0Bc",
                "DJANGO_DEBUG=False",
                f"DJANGO_ALLOWED_HOSTS={SMOKE_HOST}",
                f"DJANGO_CSRF_TRUSTED_ORIGINS=http://{SMOKE_HOST}",
                "DJANGO_SQLITE_PATH=/data/database/db.sqlite3",
                "DJANGO_MEDIA_ROOT=/data/media",
                "DJANGO_STATIC_ROOT=/data/static",
                "DJANGO_BACKUP_ROOT=/data/backups",
                "DJANGO_LOG_LEVEL=INFO",
                "GUNICORN_THREADS=2",
                "GUNICORN_TIMEOUT=60",
                "GUNICORN_GRACEFUL_TIMEOUT=30",
                "",
            )
        ),
        encoding="utf-8",
    )
    compose_env = workspace / "compose.env"
    compose_env.write_text(
        "\n".join(
            (
                f"COMPOSE_PROJECT_NAME={project_name}",
                f"WEB_IMAGE={image}",
                "NGINX_IMAGE=nginx:1.28.0-alpine",
                f"NGINX_SERVER_NAME={SMOKE_HOST}",
                # Compose appends /data/<name>; point it at the workspace root.
                f"PARTY_ARCHIVE_ROOT={workspace.as_posix()}",
                f"PRODUCTION_ENV_FILE={production_env.as_posix()}",
                "HTTP_BIND_ADDRESS=127.0.0.1",
                "HTTP_PORT=18080",
                "",
            )
        ),
        encoding="utf-8",
    )
    return production_env, compose_env


def compose_command(compose_env: Path, *arguments: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--env-file",
        str(compose_env),
        "-f",
        str(COMPOSE_FILE),
        *arguments,
    ]


def image_admin_command(image: str, production_env: Path, workspace: Path, *arguments: str) -> list[str]:
    command = [
        "docker",
        "run",
        "--rm",
        "--entrypoint",
        "python",
        "--env-file",
        str(production_env),
    ]
    for name in ("database", "media", "static", "backups"):
        command.extend(("--volume", f"{workspace / 'data' / name}:/data/{name}"))
    return [*command, image, "manage.py", *arguments]


def assert_image_contract(image: str) -> None:
    user = run(
        ["docker", "run", "--rm", "--entrypoint", "id", image, "-u"],
        capture_output=True,
    ).stdout.strip()
    if user != "10001":
        raise SmokeFailure(f"image runs as unexpected uid: {user}")

    forbidden = run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "python",
            image,
            "-c",
            (
                "from pathlib import Path; root=Path('/app'); "
                "bad=[str(p) for p in root.rglob('*') if p.name=='.env' "
                "or p.suffix.lower() in {'.xls','.xlsx','.sqlite','.sqlite3'} "
                "or '.git' in p.parts or 'tests' in p.parts]; "
                "print('\\n'.join(bad)); raise SystemExit(bool(bad))"
            ),
        ],
        check=False,
        capture_output=True,
    )
    if forbidden.returncode != 0:
        raise SmokeFailure("image contains forbidden development or data files")

    missing_environment = run(
        ["docker", "run", "--rm", image],
        check=False,
        capture_output=True,
        timeout=60,
    )
    if missing_environment.returncode == 0:
        raise SmokeFailure("image started without required production environment")


def request_http(port: int, path: str) -> tuple[int, bytes, dict[str, str]]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("GET", path, headers={"Host": SMOKE_HOST})
        response = connection.getresponse()
        return response.status, response.read(), {key.lower(): value for key, value in response.getheaders()}
    finally:
        connection.close()


def wait_for_http(timeout_seconds: int = 120) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            status, body, _ = request_http(18080, "/health/ready/")
            if status == 200 and body == b"ok\n":
                return
        except OSError as exc:
            last_error = exc
        time.sleep(2)
    raise SmokeFailure(f"HTTP readiness did not pass: {last_error}")


def assert_endpoints() -> None:
    expected = {
        "/nginx-health": b"ok\n",
        "/health/live/": b"ok\n",
        "/health/ready/": b"ok\n",
    }
    for path, expected_body in expected.items():
        status, body, _ = request_http(18080, path)
        if status != 200 or body != expected_body:
            raise SmokeFailure(f"unexpected response from {path}: {status}")
    status, body, _ = request_http(
        18080, "/static/vendor/bootstrap/5.3.3/css/bootstrap.min.css"
    )
    if status != 200 or b"Bootstrap" not in body[:500]:
        raise SmokeFailure("vendored Bootstrap CSS is unavailable through HTTP")


def assert_no_public_web_port(compose_env: Path) -> None:
    web_id = run(
        compose_command(compose_env, "ps", "-q", "web"), capture_output=True
    ).stdout.strip()
    if not web_id:
        raise SmokeFailure("web container id is unavailable")
    published = run(
        ["docker", "port", web_id, "8000/tcp"], check=False, capture_output=True
    ).stdout.strip()
    if published:
        raise SmokeFailure(f"web port 8000 is published: {published}")


def assert_branches(image: str, production_env: Path, workspace: Path) -> None:
    marker = "PARTY_BRANCH_COUNT="
    completed = run(
        [
            *image_admin_command(image, production_env, workspace, "shell", "-c"),
            (
                "from apps.students.models import PartyBranch; "
                f"print('{marker}' + str(PartyBranch.objects.count()))"
            ),
        ],
        capture_output=True,
    )
    count_lines = [
        line.removeprefix(marker).strip()
        for line in completed.stdout.splitlines()
        if line.startswith(marker)
    ]
    if count_lines != ["9"]:
        raise SmokeFailure(f"expected 9 branches, got {count_lines or 'no count marker'}")


def execute(image: str, workspace: Path, project_name: str) -> None:
    workspace.mkdir(parents=True, exist_ok=False)
    production_env, compose_env = write_runtime_files(workspace, image, project_name)
    compose_started = False
    try:
        run(["sudo", "chown", "-R", APP_UID_GID, str(workspace / "data")])
        assert_image_contract(image)
        run(image_admin_command(image, production_env, workspace, "migrate", "--noinput"))
        run(image_admin_command(image, production_env, workspace, "initialize_branches"))
        run(compose_command(compose_env, "config", "--quiet"))
        run(compose_command(compose_env, "up", "--detach"), timeout=240)
        compose_started = True
        wait_for_http()
        assert_endpoints()
        assert_no_public_web_port(compose_env)
        assert_branches(image, production_env, workspace)
        run(compose_command(compose_env, "restart", "web"), timeout=120)
        wait_for_http()
        assert_branches(image, production_env, workspace)
        print("[PASS] production container smoke test")
    finally:
        if compose_started:
            run(compose_command(compose_env, "ps"), check=False)
            run(compose_command(compose_env, "logs", "--tail", "200", "web", "nginx"), check=False)
            run(compose_command(compose_env, "down", "--remove-orphans"), check=False, timeout=120)
        for sensitive_file in (production_env,):
            sensitive_file.unlink(missing_ok=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        workspace = require_ci_workspace(args.workspace, dict(os.environ))
        execute(args.image, workspace, args.project_name)
    except (OSError, SmokeFailure, subprocess.SubprocessError) as exc:
        print(f"[FAIL] container smoke: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
