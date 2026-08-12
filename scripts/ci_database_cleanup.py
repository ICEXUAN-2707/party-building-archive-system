"""Safely remove the fixed SQLite artifacts owned by the CI workflow."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Mapping

from scripts.ci_guard import CI_SQLITE_ARTIFACT_NAMES


def validate_ci_database_path(runner_temp: Path, database_path: Path) -> Path:
    resolved_temp = runner_temp.resolve()
    resolved_database = database_path.resolve()
    if resolved_database.parent != resolved_temp or resolved_database.name != "ci.sqlite3":
        raise ValueError("refusing to clean a database outside RUNNER_TEMP")
    return resolved_temp


def clean_ci_database_artifacts(runner_temp: Path, database_path: Path) -> None:
    resolved_temp = validate_ci_database_path(runner_temp, database_path)
    for artifact_name in CI_SQLITE_ARTIFACT_NAMES:
        (resolved_temp / artifact_name).unlink(missing_ok=True)

    remaining = [
        artifact_name
        for artifact_name in CI_SQLITE_ARTIFACT_NAMES
        if (resolved_temp / artifact_name).exists()
    ]
    if remaining:
        raise OSError(f"failed to remove CI database artifacts: {remaining}")


def main(environment: Mapping[str, str] | None = None) -> int:
    if environment is None:
        environment = os.environ
    try:
        runner_temp = Path(environment["RUNNER_TEMP"])
        database_path = Path(environment["DJANGO_SQLITE_PATH"])
        clean_ci_database_artifacts(runner_temp, database_path)
    except (KeyError, OSError, ValueError) as exc:
        print(f"[FAIL] CI database cleanup: {exc}", file=sys.stderr)
        return 1

    print("[PASS] CI database artifacts removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
