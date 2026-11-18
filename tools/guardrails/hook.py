from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .custody import APPROVAL_DIR, locked_test_for
from .util import matches_any, normalize_path, read_text

DANGEROUS = [
    r"\brm\s+-rf\b",
    r"\brm\s+-fr\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+push\s+--force\b",
    r"\bchmod\s+777\b",
    r"\bcurl\b[^\n|]*\|\s*(ba)?sh\b",
    r"\bwget\b[^\n|]*\|\s*(ba)?sh\b",
    r"\bdd\s+if=",
    r">\s*/dev/sd",
]

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "Shell", "Terminal"}


def evaluate_pre_tool(root: Path, config: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    tool = str(payload.get("tool_name") or payload.get("tool") or "")
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    if tool in EDIT_TOOLS or "file_path" in tool_input:
        raw_path = str(tool_input.get("file_path") or tool_input.get("path") or "")
        if not raw_path:
            return {"decision": "allow", "reason": "no file path"}
        normalized = normalize_path(raw_path)
        protected = [str(item) for item in config.get("protected", [])]
        if matches_any(normalized, protected):
            return {
                "decision": "deny",
                "reason": f"protected path: {normalized}. Change it via ADR + human approval.",
            }
        locked_task = locked_test_for(root, normalized)
        if locked_task:
            approval = root / APPROVAL_DIR / f"{locked_task}.json"
            if not approval.exists():
                return {
                    "decision": "deny",
                    "reason": (
                        f"test file is locked for task {locked_task!r}: {normalized}. "
                        f"Run `guardrails test-approve --task {locked_task} --reason '...'` first."
                    ),
                }
            return {
                "decision": "allow",
                "reason": f"test change approved for task {locked_task!r}; re-lock after editing.",
            }
        return {"decision": "allow", "reason": f"not protected: {normalized}"}

    if tool in SHELL_TOOLS:
        command = str(tool_input.get("command") or "")
        for pattern in DANGEROUS:
            if re.search(pattern, command):
                return {
                    "decision": "deny",
                    "reason": f"dangerous shell pattern {pattern!r}: {command}",
                }
        return {"decision": "allow", "reason": "shell command not in denylist"}

    return {"decision": "allow", "reason": f"no rule for tool {tool!r}"}


def session_start_text(root: Path) -> str:
    from .state import active_task, handoff_text

    task = active_task(root)
    if task:
        return handoff_text(root, task)
    config_path = root / "guardrails.yaml"
    if not config_path.exists():
        return "guardrails: no guardrails.yaml found; read AGENTS.md before editing."
    return (
        "guardrails: read AGENTS.md. For each task run "
        "`guardrails brief --task specs/<id>` and load only the selected 1-3 chapters. "
        "Do not read the whole manual/. After compaction, restore only the card + current chapter + state.json."
    )


def test_locks(root: Path) -> dict[str, str]:
    path = root / ".guardrails" / "test-locks.json"
    if not path.exists():
        return {}
    import json

    data = json.loads(read_text(path))
    return data if isinstance(data, dict) else {}
