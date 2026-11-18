from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import load_config
from .manual import chapter_map, load_card, load_chapters
from .risk import classify
from .route import load_task
from .util import GuardrailsError, read_text, write_text

ACTIVE_PATH = ".guardrails/active-task"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def state_path(root: Path, task: str) -> Path:
    return root / "specs" / task / "state.json"


def init_state(root: Path, task: str, task_file: Path | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "task": task,
        "goal": "",
        "type": "",
        "risk": "",
        "step": 0,
        "chapter": "",
        "read": [],
        "next": "",
        "updated_at": _now(),
    }
    candidate = task_file or (root / "specs" / task / "task.yaml")
    if candidate.exists():
        parsed = load_task(candidate)
        data.update(
            {
                "goal": parsed.goal,
                "type": parsed.type,
                "risk": parsed.risk or "",
                "files": parsed.files,
            }
        )
        if not data["risk"]:
            try:
                data["risk"] = classify(parsed.files, load_config(root))["level"]
            except GuardrailsError:
                pass
    write_text(state_path(root, task), json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    set_active(root, task)
    return data


def load_state(root: Path, task: str) -> dict[str, Any] | None:
    path = state_path(root, task)
    if not path.exists():
        return None
    return json.loads(read_text(path))


def update_state(root: Path, task: str, **fields: Any) -> dict[str, Any]:
    data = load_state(root, task)
    if data is None:
        data = init_state(root, task)
    data.update(fields)
    data["updated_at"] = _now()
    write_text(state_path(root, task), json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    return data


def set_active(root: Path, task: str) -> None:
    write_text(root / ACTIVE_PATH, task)


def active_task(root: Path) -> str | None:
    path = root / ACTIVE_PATH
    if not path.exists():
        return None
    value = read_text(path).strip()
    return value or None


def handoff_text(root: Path, task: str | None = None) -> str:
    task = task or active_task(root)
    if not task:
        return (
            "guardrails: no active task. Run `guardrails state init --task <id> --task-file specs/<id>/task.yaml`."
        )
    state = load_state(root, task)
    if state is None:
        return f"guardrails: no state for task {task!r}; run `guardrails state init --task {task}`."

    lines = [
        f"# Handoff: {task}",
        "",
        "## State",
        "",
        "```json",
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
    ]

    try:
        config = load_config(root)
        card = load_card(root, config)
        lines += ["## Card", "", card.body.rstrip(), ""]
        chapter_name = str(state.get("chapter") or "")
        if chapter_name:
            chapters = chapter_map(load_chapters(root, config))
            chapter = chapters.get(chapter_name)
            if chapter:
                lines += [f"## Chapter: {chapter_name}", "", chapter.body.rstrip(), ""]
    except GuardrailsError:
        lines += ["## Card", "", "_manual/card not available_", ""]

    next_step = str(state.get("next") or "")
    if next_step:
        lines += ["## Next", "", next_step, ""]
    return "\n".join(lines)
