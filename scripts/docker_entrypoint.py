"""Production container entrypoint for the single-instance Django service."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping


def bounded_int(
    environment: Mapping[str, str],
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw = environment.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer.") from exc
    if not minimum <= value <= maximum:
        raise SystemExit(f"{name} must be between {minimum} and {maximum}.")
    return value


def build_gunicorn_command(environment: Mapping[str, str]) -> list[str]:
    threads = bounded_int(environment, "GUNICORN_THREADS", 2, minimum=1, maximum=8)
    timeout = bounded_int(environment, "GUNICORN_TIMEOUT", 60, minimum=30, maximum=300)
    graceful_timeout = bounded_int(
        environment,
        "GUNICORN_GRACEFUL_TIMEOUT",
        30,
        minimum=10,
        maximum=120,
    )
    return [
        "gunicorn",
        "config.wsgi:application",
        "--bind=0.0.0.0:8000",
        "--workers=1",
        "--worker-class=gthread",
        f"--threads={threads}",
        f"--timeout={timeout}",
        f"--graceful-timeout={graceful_timeout}",
        "--keep-alive=5",
        "--max-requests=1000",
        "--max-requests-jitter=100",
        "--error-logfile=-",
        "--capture-output",
    ]


def main() -> None:
    subprocess.run(
        [sys.executable, "manage.py", "collectstatic", "--noinput"],
        check=True,
    )
    command = build_gunicorn_command(os.environ)
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
