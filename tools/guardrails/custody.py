from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .graph import build_graph
from .util import GuardrailsError, normalize_path, read_text, sha256_text, write_text

LOCK_PATH = ".guardrails/test-locks.json"
APPROVAL_DIR = ".guardrails/test-approvals"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(path: Path) -> str:
    return "sha256:" + sha256_text(read_text(path))


def _discover_tests(root: Path, config: dict[str, Any]) -> list[str]:
    data = build_graph(root, config)
    tests = sorted(normalize_path(str(path.relative_to(root))) for path in data["tests"])
    holdout = config.get("holdout")
    if holdout:
        directory = root / str(holdout)
        if directory.exists():
            for path in sorted(directory.rglob("*")):
                if path.is_file() and path.suffix in {".py", ".ts", ".tsx", ".js", ".jsx"}:
                    tests.append(normalize_path(str(path.relative_to(root))))
    return sorted(set(tests))


def lock_tests(
    root: Path,
    config: dict[str, Any],
    task: str,
    files: list[str] | None = None,
) -> dict[str, Any]:
    selected = [normalize_path(item) for item in (files or _discover_tests(root, config))]
    locked = {}
    for item in selected:
        path = root / item
        if path.exists():
            locked[item] = _hash(path)
    data = {
        "task": task,
        "locked_at": _now(),
        "files": locked,
    }
    write_text(root / LOCK_PATH, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    approval = root / APPROVAL_DIR / f"{task}.json"
    if approval.exists():
        approval.unlink()
    return {"task": task, "locked": len(locked), "path": LOCK_PATH}


def check_tests(root: Path, task: str) -> dict[str, Any]:
    path = root / LOCK_PATH
    if not path.exists():
        return {
            "task": task,
            "locked": False,
            "ok": True,
            "changed": [],
            "missing": [],
            "approved": False,
            "needs_relock": False,
        }
    data = json.loads(read_text(path))
    locked = data.get("files", {})
    current = {}
    for item in locked:
        file_path = root / item
        if file_path.exists():
            current[item] = _hash(file_path)
    changed = sorted(item for item, digest in locked.items() if current.get(item) != digest)
    missing = sorted(item for item in locked if item not in current)
    approval = root / APPROVAL_DIR / f"{task}.json"
    approved = approval.exists()
    ok = not changed and not missing
    return {
        "task": task,
        "locked": True,
        "ok": ok,
        "changed": changed,
        "missing": missing,
        "approved": approved,
        "needs_relock": bool(changed and approved),
    }


def approve_tests(root: Path, task: str, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise GuardrailsError("test approval requires a reason")
    data = {"task": task, "reason": reason, "approved_at": _now()}
    write_text(
        root / APPROVAL_DIR / f"{task}.json",
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
    )
    return {"task": task, "approved": True, "reason": reason}


def locked_test_for(root: Path, path: str) -> str | None:
    """Return the task id if the path is locked, else None."""
    lock_path = root / LOCK_PATH
    if not lock_path.exists():
        return None
    data = json.loads(read_text(lock_path))
    task = str(data.get("task", ""))
    files = data.get("files", {})
    return task if normalize_path(path) in files else None
