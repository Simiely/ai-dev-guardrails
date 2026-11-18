from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .manual import Chapter, chapter_map, selected_token_estimate
from .risk import classify
from .util import GuardrailsError, load_yaml, matches_any, sha256_text, stable_json

PRIORITY = ["intake", "context", "change", "tdd", "review", "verify"]
DROP_ORDER = ["context", "intake", "change", "tdd", "review"]


@dataclass
class Task:
    id: str = "adhoc"
    type: str = ""
    files: list[str] = field(default_factory=list)
    goal: str = ""
    risk: str | None = None
    unfamiliar: bool = False


def load_task(path: Path) -> Task:
    if path.is_dir():
        path = path / "task.yaml"
    if not path.exists():
        raise GuardrailsError(f"missing task file: {path}")
    data = load_yaml(path)
    nested = data.get("task")
    if isinstance(nested, dict):
        merged = dict(nested)
        for key, value in data.items():
            if key != "task":
                merged[key] = value
        data = merged
    return Task(
        id=str(data.get("id") or path.parent.name),
        type=str(data.get("type") or ""),
        files=[str(item) for item in data.get("files", [])],
        goal=str(data.get("goal") or ""),
        risk=str(data["risk"]) if data.get("risk") else None,
        unfamiliar=bool(data.get("unfamiliar", False)),
    )


def select_chapters(task: Task, config: dict[str, Any], chapters: list[Chapter]) -> dict[str, Any]:
    by_name = chapter_map(chapters)
    risk = classify(task.files, config)
    level = task.risk or risk["level"]
    task_type = task.type.strip().lower()

    selected: list[str] = []

    def add(name: str) -> None:
        if name in by_name and name not in selected:
            selected.append(name)

    if task_type == "docs":
        add("verify")
    elif task_type == "bugfix":
        add("tdd")
        add("verify")
    elif task_type == "feature":
        add("change")
        add("verify")
    elif task_type == "refactor":
        add("change")
        add("verify")
    elif task_type == "review":
        add("review")
        add("verify")
    elif task_type == "release":
        add("review")
        add("verify")
    else:
        add("intake")
        add("verify")

    if task.unfamiliar and task_type in {"feature", "refactor", "bugfix"}:
        add("context")

    if level == "R3":
        add("review")

    review = by_name.get("review")
    if review and any(matches_any(file, review.globs) for file in task.files):
        add("review")

    max_loaded = int(config.get("manual", {}).get("max_loaded_per_task", 3))
    while len(selected) > max_loaded:
        for candidate in DROP_ORDER:
            if candidate in selected and candidate != "verify":
                selected.remove(candidate)
                break
        else:
            break

    budget = int(config.get("manual", {}).get("token_budget", 3000))
    tokens = selected_token_estimate(chapters, selected)
    while tokens > budget and len(selected) > 1:
        for candidate in DROP_ORDER:
            if candidate in selected and candidate != "verify":
                selected.remove(candidate)
                break
        else:
            break
        tokens = selected_token_estimate(chapters, selected)

    selected.sort(key=lambda name: PRIORITY.index(name) if name in PRIORITY else 99)
    skipped = sorted(name for name in by_name if name not in selected)

    manifest = sha256_text(
        stable_json(
            {
                "config_version": config.get("version"),
                "task": {
                    "id": task.id,
                    "type": task_type,
                    "files": sorted(task.files),
                    "risk": level,
                    "unfamiliar": task.unfamiliar,
                },
                "selected": selected,
            }
        )
    )

    reasons = [f"type={task_type or 'unknown'}", f"risk={level}", *risk["reasons"]]
    if task.unfamiliar:
        reasons.append("unfamiliar area requested")
    if len(selected) >= max_loaded:
        reasons.append(f"capped at {max_loaded} chapters")

    fallback = "ask_human" if not task_type or (not task.files and task_type not in {"review", "release"}) else "none"

    return {
        "task_id": task.id,
        "type": task_type,
        "risk": level,
        "risk_reasons": risk["reasons"],
        "modules": risk["modules"],
        "selected": selected,
        "skipped": skipped,
        "tokens": tokens,
        "budget": budget,
        "manifest": manifest,
        "fallback": fallback,
        "reasons": reasons,
    }


def brief_text(result: dict[str, Any], chapters: list[Chapter]) -> str:
    by_name = chapter_map(chapters)
    lines = [
        f"selected: {', '.join(result['selected']) or '(none)'}",
        f"risk: {result['risk']}",
        f"reason: {'; '.join(result['reasons'])}",
        f"tokens: ~{result['tokens']} / {result['budget']}",
        f"manifest: {result['manifest']}",
        f"skipped: {', '.join(result['skipped']) or '(none)'}",
        f"fallback: {result['fallback']}",
        "chapters:",
    ]
    for name in result["selected"]:
        chapter = by_name[name]
        lines.append(f"- {name}: {chapter.description}")
    raw = result.get("raw_sources") or []
    if raw:
        lines.append("raw sources:")
        for item in raw:
            if not isinstance(item, dict):
                continue
            origin = str(item.get("origin") or "")
            path = str(item.get("path") or "?")
            lines.append(f"- {path}" + (f" ({origin})" if origin else ""))
    return "\n".join(lines)
