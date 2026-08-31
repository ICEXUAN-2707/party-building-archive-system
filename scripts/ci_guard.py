"""CI repository policy checks shared by Windows and Linux runners."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PROJECT_FILES: tuple[str, ...] = (
    "AGENTS.md",
    ".env.example",
    "config/settings.py",
    "docs/spec.md",
    "manage.py",
    "requirements.txt",
    "scripts/ci_database_cleanup.py",
)

# 该清单只登记已经进入develop基线的测试，后续模块合入后由CI-03扩充。
REQUIRED_TEST_FILES: tuple[str, ...] = (
    "tests/test_ci_database_cleanup.py",
    "tests/test_ci_guard.py",
    "tests/test_excel_parser.py",
    "tests/test_foundation.py",
    "tests/test_imports_parser_header.py",
    "tests/test_settings.py",
    "tests/test_student_auth.py",
    "tests/test_student_session.py",
    "tests/test_excel_parser.py",
    "tests/test_imports_parser_header.py",
)

TEXT_SUFFIXES: frozenset[str] = frozenset(
    {
        ".cfg",
        ".css",
        ".example",
        ".html",
        ".ini",
        ".js",
        ".json",
        ".md",
        ".py",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)

SCAN_TOP_LEVEL_NAMES: frozenset[str] = frozenset(
    {
        ".github",
        "AGENTS.md",
        "README.md",
        "apps",
        "config",
        "docs",
        "scripts",
        "static",
        "templates",
        "tests",
    }
)

ABSOLUTE_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]"),  # ci-guard: allow-absolute-path
    re.compile(r"file:///"),  # ci-guard: allow-absolute-path
    re.compile(r"/Users/[^/\s]+/"),  # ci-guard: allow-absolute-path
    re.compile(r"/home/[^/\s]+/"),  # ci-guard: allow-absolute-path
)

IGNORED_DIRECTORY_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "htmlcov",
        "venv",
    }
)

CI_SQLITE_ARTIFACT_NAMES: tuple[str, ...] = tuple(
    f"{database_name}{suffix}"
    for database_name in ("ci.sqlite3", "test_ci.sqlite3")
    for suffix in ("", "-journal", "-wal", "-shm")
)

# 联合验收工具会将脱敏Excel、独立SQLite和媒体证据写入该Git忽略目录。
# 这里只豁免冻结的证据根目录，避免放宽仓库其他位置的污染检查。
POST_TEST_ARTIFACT_EXEMPT_PREFIXES: tuple[str, ...] = (
    "artifacts/acceptance/",
)


@dataclass(frozen=True)
class Problem:
    rule: str
    path: str
    message: str
    line_number: int | None = None

    def render(self) -> str:
        location = self.path
        if self.line_number is not None:
            location = f"{location}:{self.line_number}"
        return f"[FAIL] {self.rule}: {location} - {self.message}"


def _run_git(*arguments: str, root: Path = PROJECT_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def get_tracked_files(root: Path = PROJECT_ROOT) -> list[str]:
    completed = _run_git("ls-files", root=root)
    return [line.strip().replace("\\", "/") for line in completed.stdout.splitlines() if line.strip()]


def find_missing_required_files(
    root: Path,
    required_files: Sequence[str],
) -> list[Problem]:
    return [
        Problem("required-file", relative_path, "required file is missing")
        for relative_path in required_files
        if not (root / relative_path).is_file()
    ]


def _is_forbidden_tracked_file(relative_path: str) -> str | None:
    normalized = relative_path.replace("\\", "/")
    path = Path(normalized)
    lowered_parts = tuple(part.lower() for part in path.parts)
    lowered_name = path.name.lower()

    if normalized == ".env" or lowered_name in {"db.sqlite3", "db.sqlite3-journal"}:
        return "environment file or SQLite database must not be tracked"
    if path.suffix.lower() in {".xls", ".xlsx"}:
        return "Excel files must not be tracked"
    if path.suffix.lower() in {".pyc", ".pyo"} or "__pycache__" in lowered_parts:
        return "Python cache files must not be tracked"
    if lowered_parts and lowered_parts[0] in {".venv", "env", "venv"}:
        return "virtual environments must not be tracked"
    if normalized.startswith("media/imports/") and normalized != "media/imports/.gitkeep":
        return "uploaded import files must not be tracked"
    if lowered_name.endswith((".bak", ".backup", ".sqlite", ".sqlite3")) and normalized != ".env.example":
        return "database or backup artifacts must not be tracked"
    return None


def find_forbidden_tracked_files(tracked_files: Iterable[str]) -> list[Problem]:
    problems: list[Problem] = []
    for relative_path in tracked_files:
        message = _is_forbidden_tracked_file(relative_path)
        if message:
            problems.append(Problem("forbidden-tracked-file", relative_path, message))
    return problems


def _should_scan_text_file(relative_path: str) -> bool:
    path = Path(relative_path)
    if not path.parts or path.parts[0] not in SCAN_TOP_LEVEL_NAMES:
        return False
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {"AGENTS.md", "README.md"}


def find_absolute_paths(root: Path, tracked_files: Iterable[str]) -> list[Problem]:
    problems: list[Problem] = []
    for relative_path in tracked_files:
        if not _should_scan_text_file(relative_path):
            continue
        file_path = root / relative_path
        if not file_path.is_file():
            continue
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if "ci-guard: allow-absolute-path" in line:
                continue
            if any(pattern.search(line) for pattern in ABSOLUTE_PATH_PATTERNS):
                problems.append(
                    Problem(
                        "absolute-local-path",
                        relative_path,
                        "developer-specific absolute path found",
                        line_number,
                    )
                )
    return problems


def _iter_repository_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        relative_parts = path.relative_to(root).parts
        if any(part in IGNORED_DIRECTORY_NAMES for part in relative_parts):
            continue
        if path.is_file():
            yield path


def find_post_test_artifacts(root: Path) -> list[Problem]:
    problems: list[Problem] = []
    for file_path in _iter_repository_files(root):
        relative_path = file_path.relative_to(root).as_posix()
        if relative_path.startswith(POST_TEST_ARTIFACT_EXEMPT_PREFIXES):
            continue
        lowered_name = file_path.name.lower()
        if relative_path in {"db.sqlite3", "db.sqlite3-journal"}:
            problems.append(
                Problem("post-test-artifact", relative_path, "test created a repository-local database")
            )
        elif file_path.suffix.lower() in {".xls", ".xlsx"}:
            problems.append(
                Problem("post-test-artifact", relative_path, "Excel test artifact was not cleaned up")
            )
        elif relative_path.startswith("media/imports/") and relative_path != "media/imports/.gitkeep":
            problems.append(
                Problem("post-test-artifact", relative_path, "uploaded test artifact was not cleaned up")
            )
        elif lowered_name.endswith((".bak", ".backup")):
            problems.append(
                Problem("post-test-artifact", relative_path, "backup test artifact was not cleaned up")
            )
    return problems


def find_ci_temp_database_artifacts(temp_dir: Path) -> list[Problem]:
    """Report only the fixed SQLite artifacts owned by the CI workflow."""
    problems: list[Problem] = []
    for artifact_name in CI_SQLITE_ARTIFACT_NAMES:
        artifact_path = temp_dir / artifact_name
        if artifact_path.exists():
            problems.append(
                Problem(
                    "ci-temp-database-artifact",
                    artifact_path.as_posix(),
                    "CI SQLite artifact was not cleaned up",
                )
            )
    return problems


def collect_problems(
    root: Path,
    *,
    post_test: bool = False,
    temp_dir: Path | None = None,
) -> list[Problem]:
    tracked_files = get_tracked_files(root)
    problems = find_missing_required_files(root, REQUIRED_PROJECT_FILES)
    problems.extend(find_missing_required_files(root, REQUIRED_TEST_FILES))
    problems.extend(find_forbidden_tracked_files(tracked_files))
    problems.extend(find_absolute_paths(root, tracked_files))
    if post_test:
        problems.extend(find_post_test_artifacts(root))
    if temp_dir is not None:
        problems.extend(find_ci_temp_database_artifacts(temp_dir))
    return problems


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--post-test",
        action="store_true",
        help="also check for database, Excel, upload, and backup artifacts left by tests",
    )
    parser.add_argument(
        "--temp-dir",
        type=Path,
        help="also check the named CI temporary directory for fixed SQLite artifacts",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        problems = collect_problems(
            PROJECT_ROOT,
            post_test=args.post_test,
            temp_dir=args.temp_dir,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[ERROR] ci-guard: {exc}", file=sys.stderr)
        return 2

    if problems:
        for problem in problems:
            print(problem.render(), file=sys.stderr)
        print(f"[FAIL] ci-guard found {len(problems)} problem(s)", file=sys.stderr)
        return 1

    mode = "post-test repository state" if args.post_test else "repository policy"
    print(f"[PASS] {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
