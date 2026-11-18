from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .util import GuardrailsError, read_text


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_run(
    root: Path,
    task: str,
    status: str,
    tests_total: int = 0,
    tests_failed: int = 0,
    duration: float = 0.0,
    rework: bool = False,
    note: str = "",
) -> dict[str, Any]:
    if status not in {"pass", "fail"}:
        raise GuardrailsError("status must be pass or fail")
    record = {
        "timestamp": _now(),
        "task": task,
        "status": status,
        "tests_total": int(tests_total),
        "tests_failed": int(tests_failed),
        "duration": float(duration),
        "rework": bool(rework),
        "note": note,
    }
    path = root / ".guardrails" / "metrics.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def ingest_junit(root: Path, file: Path, task: str) -> dict[str, Any]:
    if not file.exists():
        raise GuardrailsError(f"missing JUnit file: {file}")
    tree = ET.parse(file)
    root_node = tree.getroot()
    suites = [root_node] if root_node.tag == "testsuite" else root_node.findall(".//testsuite")
    total = failures = errors = 0
    duration = 0.0
    for suite in suites:
        total += int(suite.get("tests", 0) or 0)
        failures += int(suite.get("failures", 0) or 0)
        errors += int(suite.get("errors", 0) or 0)
        duration += float(suite.get("time", 0) or 0)
    status = "pass" if failures + errors == 0 else "fail"
    return record_run(
        root,
        task=task,
        status=status,
        tests_total=total,
        tests_failed=failures + errors,
        duration=duration,
        note=f"junit:{file.name}",
    )


def metrics_report(root: Path) -> dict[str, Any]:
    path = root / ".guardrails" / "metrics.jsonl"
    if not path.exists():
        return {
            "runs": 0,
            "pass_rate": 0.0,
            "run_failure_rate": 0.0,
            "rework_rate": 0.0,
            "avg_failed_tests": 0.0,
            "by_task": {},
        }
    records = [json.loads(line) for line in read_text(path).splitlines() if line.strip()]
    runs = len(records)
    passed = sum(1 for item in records if item.get("status") == "pass")
    rework = sum(1 for item in records if item.get("rework"))
    failed_tests = sum(int(item.get("tests_failed", 0)) for item in records)
    by_task: dict[str, dict[str, Any]] = {}
    for item in records:
        task = str(item.get("task", "unknown"))
        bucket = by_task.setdefault(task, {"runs": 0, "passed": 0, "rework": 0})
        bucket["runs"] += 1
        bucket["passed"] += 1 if item.get("status") == "pass" else 0
        bucket["rework"] += 1 if item.get("rework") else 0
    return {
        "runs": runs,
        "pass_rate": round(passed / runs, 4) if runs else 0.0,
        "run_failure_rate": round((runs - passed) / runs, 4) if runs else 0.0,
        "rework_rate": round(rework / runs, 4) if runs else 0.0,
        "avg_failed_tests": round(failed_tests / runs, 2) if runs else 0.0,
        "by_task": by_task,
    }


def render_metrics(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "METRICS",
            f"- runs: {report['runs']}",
            f"- pass rate: {report['pass_rate']}",
            f"- run failure rate (local proxy): {report['run_failure_rate']}",
            f"- rework rate: {report['rework_rate']}",
            f"- avg failed tests: {report['avg_failed_tests']}",
        ]
    )
