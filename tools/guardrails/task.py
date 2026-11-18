from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .util import GuardrailsError, read_text, write_text

TEMPLATE_FILES = {
    "task": "templates/task.yaml",
    "intent": "templates/intent.md",
    "spec": "templates/spec.md",
    "plan": "templates/plan.md",
}

DEFAULT_TASK = """id: {{ID}}
type: {{TYPE}}
goal: {{TITLE}}
files: []
risk: {{TIER}}
unfamiliar: false
"""


def _template(root: Path, name: str) -> str:
    path = root / TEMPLATE_FILES[name]
    if path.exists():
        return read_text(path)
    if name == "task":
        return DEFAULT_TASK
    raise GuardrailsError(f"missing template: {path}")


def _render(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def create_task(
    root: Path,
    task_id: str,
    title: str,
    task_type: str = "feature",
    risk: str = "R1",
    files: list[str] | None = None,
) -> dict[str, Any]:
    if not task_id or any(char in task_id for char in "/\\"):
        raise GuardrailsError("task id must be a simple name")
    risk = risk.upper()
    if risk not in {"R0", "R1", "R2", "R3"}:
        raise GuardrailsError(f"invalid risk: {risk}; use R0, R1, R2 or R3")

    target = root / "specs" / task_id
    if target.exists():
        raise GuardrailsError(f"task already exists: {target}")

    values = {
        "ID": task_id,
        "TITLE": title,
        "TYPE": task_type,
        "TIER": risk,
        "DATE": date.today().isoformat(),
    }
    target.mkdir(parents=True, exist_ok=True)

    task_text = _render(_template(root, "task"), values)
    if files:
        task_text = task_text.replace(
            "files: []",
            "files:\n" + "\n".join(f"  - {item}" for item in files),
        )
    created = ["task.yaml"]
    write_text(target / "task.yaml", task_text)

    raw = target / "raw"
    raw.mkdir()
    manifest = {
        "task": task_id,
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": [],
    }
    write_text(raw / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    created.append("raw/manifest.json")

    trace_template = root / "templates" / "trace.yaml"
    if trace_template.exists():
        write_text(target / "trace.yaml", read_text(trace_template))
        created.append("trace.yaml")

    if risk == "R0":
        documents = ["plan"]
    elif risk == "R1":
        documents = ["intent", "spec"]
    else:
        documents = ["intent", "spec", "plan"]

    for name in documents:
        write_text(target / f"{name}.md", _render(_template(root, name), values))
        created.append(f"{name}.md")

    return {"task": task_id, "path": str(target), "created": created}
