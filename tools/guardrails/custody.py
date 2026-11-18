from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .graph import build_graph
from .util import GuardrailsError, normalize_path, read_text, sha256_text, write_text

LOCK_DIR = ".guardrails/test-locks"
LEGACY_LOCK_PATH = ".guardrails/test-locks.json"
APPROVAL_DIR = ".guardrails/test-approvals"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(path: Path) -> str:
    return "sha256:" + sha256_text(read_text(path))


def lock_path(root: Path, task: str) -> Path:
    return root / LOCK_DIR / f"{task}.json"


def _read_lock(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


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
    path = lock_path(root, task)
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))

    legacy = root / LEGACY_LOCK_PATH
    legacy_data = _read_lock(legacy)
    if legacy_data is not None and str(legacy_data.get("task") or "") == task:
        legacy.unlink()

    approval = root / APPROVAL_DIR / f"{task}.json"
    if approval.exists():
        approval.unlink()
    return {
        "task": task,
        "locked": len(locked),
        "path": normalize_path(str(path.relative_to(root))),
    }


def check_tests(root: Path, task: str) -> dict[str, Any]:
    path = lock_path(root, task)
    legacy_task: str | None = None
    if not path.exists():
        legacy = root / LEGACY_LOCK_PATH
        legacy_data = _read_lock(legacy)
        if legacy_data is not None:
            legacy_task = str(legacy_data.get("task") or "")
            if legacy_task == task:
                path = legacy

    if not path.exists():
        return {
            "task": task,
            "locked": False,
            "ok": True,
            "changed": [],
            "missing": [],
            "approved": False,
            "needs_relock": False,
            "legacy_task": legacy_task,
        }

    data = _read_lock(path)
    if data is None:
        return {
            "task": task,
            "locked": False,
            "ok": False,
            "changed": [],
            "missing": [],
            "approved": False,
            "needs_relock": False,
            "error": f"invalid lock file: {path}",
            "legacy_task": legacy_task,
        }

    lock_task = str(data.get("task") or task)
    locked = data.get("files", {})
    if not isinstance(locked, dict):
        locked = {}
    current = {}
    for item in locked:
        file_path = root / item
        if file_path.exists():
            current[item] = _hash(file_path)
    changed = sorted(item for item, digest in locked.items() if current.get(item) != digest)
    missing = sorted(item for item in locked if item not in current)
    approval = root / APPROVAL_DIR / f"{task}.json"
    approved = approval.exists()
    ok = lock_task == task and not changed and not missing
    return {
        "task": task,
        "locked": True,
        "lock_task": lock_task,
        "ok": ok,
        "changed": changed,
        "missing": missing,
        "approved": approved,
        "needs_relock": bool(changed and approved),
        "legacy_task": legacy_task,
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


def _lock_entries(root: Path) -> list[tuple[str, dict[str, str]]]:
    entries: list[tuple[str, dict[str, str]]] = []
    lock_dir = root / LOCK_DIR
    if lock_dir.exists():
        for path in sorted(lock_dir.glob("*.json")):
            data = _read_lock(path)
            if data is None:
                continue
            files = data.get("files", {})
            if isinstance(files, dict):
                entries.append((str(data.get("task") or path.stem), files))
    legacy_data = _read_lock(root / LEGACY_LOCK_PATH)
    if legacy_data is not None:
        files = legacy_data.get("files", {})
        if isinstance(files, dict):
            entries.append((str(legacy_data.get("task") or "legacy"), files))
    return entries


def locked_tasks_for(root: Path, path: str) -> list[str]:
    normalized = normalize_path(path)
    tasks: list[str] = []
    for task, files in _lock_entries(root):
        if normalized in files and task not in tasks:
            tasks.append(task)
    return tasks


def locked_test_for(root: Path, path: str) -> str | None:
    tasks = locked_tasks_for(root, path)
    return tasks[0] if tasks else None
