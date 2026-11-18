from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .util import GuardrailsError, read_text, sha256_text, stable_json, write_text

NON_BREAKING_KEYS = {
    "description",
    "summary",
    "title",
    "example",
    "examples",
    "tags",
    "deprecated",
    "externalDocs",
}
BREAKING_SCALAR_KEYS = {"type", "format", "pattern", "minimum", "maximum", "minLength", "maxLength"}


def load_document(path: Path) -> Any:
    if not path.exists():
        raise GuardrailsError(f"missing contract file: {path}")
    text = read_text(path)
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def snapshot_document(path: Path) -> dict[str, Any]:
    document = load_document(path)
    canonical = stable_json(document)
    return {
        "path": str(path),
        "hash": "sha256:" + sha256_text(canonical),
        "document": document,
    }


def write_snapshot(path: Path, out: Path) -> dict[str, Any]:
    snapshot = snapshot_document(path)
    write_text(out, json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    return snapshot


def _is_breaking_removed(path: str, key: str) -> bool:
    if key.startswith("x-") or key in NON_BREAKING_KEYS:
        return False
    if path.endswith((".paths", ".properties", ".responses", ".parameters", ".schemas", ".components")):
        return True
    return True


def _diff(base: Any, current: Any, path: str, changes: list[dict[str, Any]]) -> None:
    if type(base) is not type(current):
        changes.append(
            {
                "path": path,
                "kind": "type_changed",
                "breaking": True,
                "detail": f"{type(base).__name__} -> {type(current).__name__}",
            }
        )
        return

    if isinstance(base, dict):
        for key in sorted(set(base) - set(current)):
            changes.append(
                {
                    "path": f"{path}.{key}",
                    "kind": "removed",
                    "breaking": _is_breaking_removed(path, key),
                    "detail": "removed",
                }
            )
        for key in sorted(set(current) - set(base)):
            changes.append(
                {
                    "path": f"{path}.{key}",
                    "kind": "added",
                    "breaking": False,
                    "detail": "added",
                }
            )
        for key in sorted(set(base) & set(current)):
            if key in {"required", "enum"}:
                continue
            _diff(base[key], current[key], f"{path}.{key}", changes)

        if isinstance(base.get("required"), list) and isinstance(current.get("required"), list):
            for value in sorted(set(current["required"]) - set(base["required"])):
                changes.append(
                    {
                        "path": f"{path}.required",
                        "kind": "required_added",
                        "breaking": True,
                        "detail": str(value),
                    }
                )
            for value in sorted(set(base["required"]) - set(current["required"])):
                changes.append(
                    {
                        "path": f"{path}.required",
                        "kind": "required_removed",
                        "breaking": False,
                        "detail": str(value),
                    }
                )

        if isinstance(base.get("enum"), list) and isinstance(current.get("enum"), list):
            base_values, current_values = set(map(str, base["enum"])), set(map(str, current["enum"]))
            if current_values < base_values:
                changes.append(
                    {
                        "path": f"{path}.enum",
                        "kind": "enum_narrowed",
                        "breaking": True,
                        "detail": f"{sorted(base_values)} -> {sorted(current_values)}",
                    }
                )
            elif base_values != current_values:
                changes.append(
                    {
                        "path": f"{path}.enum",
                        "kind": "enum_changed",
                        "breaking": False,
                        "detail": f"{sorted(base_values)} -> {sorted(current_values)}",
                    }
                )

    elif isinstance(base, list):
        if base != current:
            changes.append(
                {
                    "path": path,
                    "kind": "list_changed",
                    "breaking": False,
                    "detail": "list changed",
                }
            )

    elif base != current:
        key = path.rsplit(".", 1)[-1]
        changes.append(
            {
                "path": path,
                "kind": "value_changed",
                "breaking": key in BREAKING_SCALAR_KEYS,
                "detail": f"{base!r} -> {current!r}",
            }
        )


def diff_documents(base: Any, current: Any) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    _diff(base, current, "$", changes)
    breaking = [change for change in changes if change["breaking"]]
    non_breaking = [change for change in changes if not change["breaking"]]
    return {
        "breaking": breaking,
        "non_breaking": non_breaking,
        "summary": {
            "total": len(changes),
            "breaking": len(breaking),
            "non_breaking": len(non_breaking),
        },
    }


def diff_snapshot(base_snapshot: Path, current: Path) -> dict[str, Any]:
    if not base_snapshot.exists():
        raise GuardrailsError(f"missing base snapshot: {base_snapshot}")
    base_data = json.loads(read_text(base_snapshot))
    base = base_data.get("document", base_data)
    return diff_documents(base, load_document(current))
