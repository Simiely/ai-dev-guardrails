from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .util import GuardrailsError, load_yaml, normalize_path, read_text


def _hash_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_hash(value: str) -> str:
    value = value.strip()
    return value if value.startswith("sha256:") else f"sha256:{value}"


def _line_count(path: Path) -> int:
    return len(read_text(path).splitlines())


def _git() -> str | None:
    git = shutil.which("git")
    if git:
        return git
    candidate = Path(r"C:\Program Files\Git\cmd\git.exe")
    return str(candidate) if candidate.exists() else None


def _commit_has_path(root: Path, commit: str, path: str) -> bool | None:
    git = _git()
    if not git:
        return None
    proc = subprocess.run(
        [git, "cat-file", "-e", f"{commit}:{path}"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def _check_lines(value: str, count: int) -> str | None:
    raw = value.strip()
    if not raw:
        return None
    match = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", raw)
    if not match:
        return f"invalid line range: {value!r}"
    start = int(match.group(1))
    end = int(match.group(2) or start)
    if start < 1 or end < start or end > count:
        return f"line range {start}-{end} outside file ({count} lines)"
    return None


def _check_claim(
    root: Path,
    task: str,
    index: int,
    item: dict[str, Any],
    require_sources: bool,
) -> dict[str, Any]:
    claim_id = str(item.get("id") or f"C{index}")
    claim = str(item.get("claim") or "").strip()
    source = normalize_path(str(item.get("source") or ""))
    errors: list[str] = []
    warnings: list[str] = []

    if not claim:
        warnings.append(f"{task}/{claim_id}: empty claim text")
    if not source:
        message = f"{task}/{claim_id}: missing source"
        if require_sources:
            errors.append(message)
        else:
            warnings.append(message)
        return {"id": claim_id, "source": "", "ok": not errors, "errors": errors, "warnings": warnings}

    path = Path(source)
    if not path.is_absolute():
        task_relative = root / "specs" / task / path
        root_relative = root / path
        path = task_relative if task_relative.exists() else root_relative
    if not path.exists():
        errors.append(f"{task}/{claim_id}: source not found: {source}")
        return {"id": claim_id, "source": source, "ok": False, "errors": errors, "warnings": warnings}

    try:
        git_path = normalize_path(str(path.relative_to(root)))
    except ValueError:
        git_path = source

    expected_hash = str(item.get("sha256") or "").strip()
    if expected_hash:
        actual = _hash_file(path)
        if _normalize_hash(expected_hash) != actual:
            errors.append(
                f"{task}/{claim_id}: sha256 mismatch for {source} "
                f"(expected {_normalize_hash(expected_hash)}, got {actual})"
            )

    commit = str(item.get("commit") or "").strip()
    if commit:
        exists = _commit_has_path(root, commit, git_path)
        if exists is None:
            warnings.append(f"{task}/{claim_id}: git not found; skipped commit check")
        elif not exists:
            errors.append(f"{task}/{claim_id}: {git_path} not found at commit {commit}")

    lines = str(item.get("lines") or "").strip()
    if lines:
        problem = _check_lines(lines, _line_count(path))
        if problem:
            errors.append(f"{task}/{claim_id}: {problem}")

    return {"id": claim_id, "source": source, "ok": not errors, "errors": errors, "warnings": warnings}


def verify_trace(
    root: Path,
    task: str | None = None,
    all_tasks: bool = False,
    require_sources: bool = False,
) -> dict[str, Any]:
    specs = root / "specs"
    if all_tasks:
        tasks = sorted(path.parent.name for path in specs.glob("*/trace.yaml"))
    elif task:
        tasks = [task]
    else:
        raise GuardrailsError("pass a task id or --all")

    results: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []

    for name in tasks:
        path = specs / name / "trace.yaml"
        if not path.exists():
            message = f"{name}: missing specs/{name}/trace.yaml"
            errors.append(message)
            results.append({"task": name, "ok": False, "claims": [], "errors": [message], "warnings": []})
            continue
        data = load_yaml(path)
        claims = data.get("claims", [])
        if not isinstance(claims, list):
            message = f"{name}: trace.yaml claims must be a list"
            errors.append(message)
            results.append({"task": name, "ok": False, "claims": [], "errors": [message], "warnings": []})
            continue
        acceptance = data.get("acceptance", [])
        checked_acceptance: list[dict[str, Any]] = []
        if acceptance:
            if not isinstance(acceptance, list):
                message = f"{name}: trace.yaml acceptance must be a list"
                errors.append(message)
                checked_acceptance.append({"ok": False, "errors": [message], "warnings": []})
            else:
                for index, item in enumerate(acceptance, 1):
                    if not isinstance(item, dict):
                        message = f"{name}/A{index}: acceptance must be a mapping"
                        errors.append(message)
                        checked_acceptance.append({"ok": False, "errors": [message], "warnings": []})
                        continue
                    missing = [
                        field
                        for field in ("criterion", "test")
                        if not str(item.get(field) or "").strip()
                    ]
                    if missing:
                        message = f"{name}/A{index}: missing {', '.join(missing)}"
                        warnings.append(message)
                        checked_acceptance.append({"ok": True, "errors": [], "warnings": [message]})
                    else:
                        checked_acceptance.append({"ok": True, "errors": [], "warnings": []})
        checked = []
        for index, item in enumerate(claims, 1):
            if not isinstance(item, dict):
                message = f"{name}/C{index}: claim must be a mapping"
                errors.append(message)
                checked.append({"id": f"C{index}", "ok": False, "errors": [message], "warnings": []})
                continue
            result = _check_claim(root, name, index, item, require_sources)
            checked.append(result)
            errors.extend(result["errors"])
            warnings.extend(result["warnings"])
        if not claims and not acceptance:
            warnings.append(f"{name}: trace.yaml has no acceptance or claims")
        results.append(
            {
                "task": name,
                "ok": not any(not item["ok"] for item in checked + checked_acceptance),
                "acceptance": checked_acceptance,
                "claims": checked,
                "errors": [item for result in checked for item in result["errors"]],
                "warnings": [item for result in checked for item in result["warnings"]],
            }
        )

    if all_tasks and not tasks:
        warnings.append("no trace.yaml files found under specs/")

    return {
        "ok": not errors,
        "tasks": results,
        "errors": errors,
        "warnings": warnings,
        "checked": len(tasks),
    }


def raw_sources(root: Path, task: str) -> list[dict[str, Any]]:
    manifest = root / "specs" / task / "raw" / "manifest.json"
    if not manifest.exists():
        return []
    try:
        data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    sources = data.get("sources", [])
    return sources if isinstance(sources, list) else []


def add_raw_source(
    root: Path,
    task: str,
    source: Path,
    origin: str = "",
    force: bool = False,
) -> dict[str, Any]:
    if not source.exists() or not source.is_file():
        raise GuardrailsError(f"source not found: {source}")
    raw_dir = root / "specs" / task / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / source.name
    if dest.resolve() != source.resolve():
        if dest.exists() and not force:
            raise GuardrailsError(f"raw file already exists: {dest}; use --force")
        shutil.copy2(source, dest)

    manifest_path = raw_dir / "manifest.json"
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}
    if not isinstance(data, dict):
        data = {}
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        sources = []

    relative = f"raw/{dest.name}"
    entry = {
        "path": relative,
        "origin": origin or str(source),
        "sha256": _hash_file(dest),
        "added_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    sources = [
        item
        for item in sources
        if not (isinstance(item, dict) and item.get("path") == relative)
    ]
    sources.append(entry)
    data.update(
        {
            "task": task,
            "captured_at": data.get("captured_at") or entry["added_at"],
            "sources": sources,
        }
    )
    manifest_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return entry
