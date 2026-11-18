from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .custody import LEGACY_LOCK_PATH, LOCK_DIR
from .graph import build_graph
from .manual import load_card, load_chapters
from .metrics import metrics_report
from .util import GuardrailsError, read_text


def build_report(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    graph = build_graph(root, config)
    tests = [str(path.relative_to(root)) for path in graph["tests"]]

    snapshots = []
    contracts_dir = root / ".guardrails" / "contracts"
    if contracts_dir.exists():
        snapshots = sorted(path.name for path in contracts_dir.glob("*.json"))

    locks: dict[str, str] = {}
    lock_dir = root / LOCK_DIR
    if lock_dir.exists():
        for path in sorted(lock_dir.glob("*.json")):
            data = json.loads(read_text(path))
            files = data.get("files", {}) if isinstance(data, dict) else {}
            if isinstance(files, dict):
                locks.update(files)
    legacy = root / LEGACY_LOCK_PATH
    if legacy.exists():
        data = json.loads(read_text(legacy))
        files = data.get("files", {}) if isinstance(data, dict) else {}
        if isinstance(files, dict):
            for key, value in files.items():
                locks.setdefault(key, value)

    tasks = []
    specs_dir = root / "specs"
    if specs_dir.exists():
        for path in sorted(specs_dir.glob("*/state.json")):
            data = json.loads(read_text(path))
            tasks.append(
                {
                    "task": data.get("task"),
                    "type": data.get("type"),
                    "risk": data.get("risk"),
                    "step": data.get("step"),
                    "chapter": data.get("chapter"),
                }
            )

    try:
        card = load_card(root, config)
        chapters = load_chapters(root, config)
        manual = {"card_lines": card.lines, "chapters": len(chapters)}
    except GuardrailsError:
        manual = {"card_lines": 0, "chapters": 0}

    return {
        "tests": len(tests),
        "files": len(graph["files"]),
        "modules": len(config.get("modules", [])),
        "contract_snapshots": snapshots,
        "locked_tests": len(locks),
        "tasks": tasks,
        "manual": manual,
        "metrics": metrics_report(root),
        "metrics_note": "structural signals + local run ledger; PR/DORA history still needs CI data",
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "REPORT",
        f"- files: {report['files']}",
        f"- tests: {report['tests']}",
        f"- modules: {report['modules']}",
        f"- contract snapshots: {len(report['contract_snapshots'])}",
        f"- locked tests: {report['locked_tests']}",
        f"- tasks with state: {len(report['tasks'])}",
        f"- manual: card={report['manual']['card_lines']} lines, chapters={report['manual']['chapters']}",
        f"- metrics: runs={report['metrics']['runs']}, "
        f"pass={report['metrics']['pass_rate']}, "
        f"fail={report['metrics']['run_failure_rate']}, "
        f"rework={report['metrics']['rework_rate']}",
        f"- note: {report['metrics_note']}",
    ]
    for task in report["tasks"]:
        lines.append(
            f"  - {task['task']}: risk={task['risk'] or '-'} step={task['step']} chapter={task['chapter'] or '-'}"
        )
    return "\n".join(lines)
