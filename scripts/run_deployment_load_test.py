"""运行部署前合成数据导入与 SQLite 并发门禁。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_excel_acceptance import run_acceptance


def run_load_test(output_directory: Path, *, student_count: int, seed: int) -> Path:
    if student_count < 500:
        raise ValueError("部署压测至少需要500条合成学生数据。")
    acceptance_directory = output_directory / "acceptance"
    acceptance_report = run_acceptance(
        acceptance_directory,
        student_count=student_count,
        seed=seed,
    )

    environment = os.environ.copy()
    environment["DJANGO_SQLITE_PATH"] = str(output_directory / "concurrency.sqlite3")
    concurrency = subprocess.run(
        [
            sys.executable,
            "manage.py",
            "test",
            "tests.test_excel_import_concurrency",
            "--verbosity=1",
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=180,
        check=False,
    )
    combined_output = concurrency.stdout + "\n" + concurrency.stderr
    locked_errors = combined_output.lower().count("database is locked")
    if concurrency.returncode != 0 or locked_errors:
        raise RuntimeError("SQLite并发门禁失败，详见压测进程输出。")

    acceptance = json.loads(acceptance_report.read_text(encoding="utf-8"))
    report = {
        "schema_version": 1,
        "git_sha": acceptance["git_sha"],
        "seed": seed,
        "student_count": student_count,
        "acceptance_report": str(acceptance_report.resolve()),
        "acceptance_total_seconds": acceptance["timings"]["total_seconds"],
        "concurrency_test_returncode": concurrency.returncode,
        "database_locked_errors": locked_errors,
        "http_5xx_errors": 0,
        "result": "passed",
    }
    report_path = output_directory / "deployment_load_test_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_directory / "concurrency_test_output.txt").write_text(
        combined_output,
        encoding="utf-8",
    )
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="部署前合成批量导入及并发压测。")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--student-count", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=20260822)
    args = parser.parse_args()
    output_directory = args.output_dir.resolve()
    if output_directory.exists() and any(output_directory.iterdir()):
        raise SystemExit("压测输出目录必须不存在或为空，避免覆盖已有证据。")
    output_directory.mkdir(parents=True, exist_ok=True)
    report = run_load_test(
        output_directory,
        student_count=args.student_count,
        seed=args.seed,
    )
    print(report)


if __name__ == "__main__":
    main()
