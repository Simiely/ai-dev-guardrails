from __future__ import annotations

from pathlib import Path
from typing import Any

from .manual import Chapter
from .route import load_task, select_chapters
from .util import load_yaml


def evaluate_routing(
    root: Path,
    config: dict[str, Any],
    chapters: list[Chapter],
    suite_dir: Path,
) -> dict[str, Any]:
    max_loaded = int(config.get("manual", {}).get("max_loaded_per_task", 3))
    cases: list[dict[str, Any]] = []

    for path in sorted(suite_dir.glob("*.yaml")):
        data = load_yaml(path)
        task = load_task(path)
        expected = [str(item) for item in data.get("expect", [])]
        result = select_chapters(task, config, chapters)
        selected = result["selected"]
        selected_set = set(selected)
        expected_set = set(expected)
        hit = expected_set & selected_set
        missing = sorted(expected_set - selected_set)
        extra = sorted(selected_set - expected_set)
        recall = len(hit) / len(expected_set) if expected_set else 1.0
        over_load = len(extra) / len(selected) if selected else 0.0
        passed = not missing and len(selected) <= max_loaded
        cases.append(
            {
                "id": task.id,
                "expected": expected,
                "selected": selected,
                "missing": missing,
                "extra": extra,
                "recall": round(recall, 4),
                "over_load": round(over_load, 4),
                "tokens": result["tokens"],
                "passed": passed,
            }
        )

    total = len(cases)
    recall = sum(case["recall"] for case in cases) / total if total else 1.0
    zero_load = sum(1 for case in cases if not case["selected"]) / total if total else 0.0
    over_load = sum(case["over_load"] for case in cases) / total if total else 0.0
    token_avg = sum(case["tokens"] for case in cases) / total if total else 0
    passed = all(case["passed"] for case in cases)

    return {
        "passed": passed,
        "total": total,
        "recall": round(recall, 4),
        "zero_load": round(zero_load, 4),
        "over_load": round(over_load, 4),
        "token_avg": round(token_avg, 1),
        "cases": cases,
    }
