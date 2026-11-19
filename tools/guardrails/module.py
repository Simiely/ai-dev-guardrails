from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from .util import GuardrailsError, resolve_under

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def module_root(root: Path, config: dict[str, Any]) -> Path:
    project = config.get("project", {})
    value = str(project.get("module_root") or "modules").replace("\\", "/").strip("/")
    if not value:
        raise GuardrailsError("project.module_root is empty")
    return resolve_under(root, value)


def create_module(
    root: Path,
    config: dict[str, Any],
    name: str,
    path: str | None = None,
    layer: str = "",
    owner: str = "",
) -> dict[str, Any]:
    if not NAME_RE.match(name):
        raise GuardrailsError("module name must match ^[a-z0-9][a-z0-9-]*$")

    root_resolved = root.resolve()
    template = module_root(root, config) / "_template"
    if not template.exists():
        raise GuardrailsError(f"missing module template: {template}")

    target = resolve_under(root, path) if path else module_root(root, config) / name
    if target.exists():
        raise GuardrailsError(f"module already exists: {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, target)
    for file in target.rglob("*.md"):
        text = file.read_text(encoding="utf-8")
        file.write_text(text.replace("<name>", name), encoding="utf-8")

    relative = target.relative_to(root_resolved).as_posix()
    snippet = {
        "name": name,
        "path": relative,
        "layer": layer or "<layer>",
        "owner": owner or "<owner>",
        "contract": f"{relative}/CONTRACT.md",
    }
    public_candidates = [
        f"{relative}/CONTRACT.ts",
        f"{relative}/CONTRACT.py",
        f"{relative}/index.ts",
        f"{relative}/index.py",
    ]
    public_path = next(
        (item for item in public_candidates if (root_resolved / item).exists()),
        None,
    )
    if public_path:
        snippet["public_path"] = public_path

    return {
        "name": name,
        "path": relative,
        "template": template.relative_to(root_resolved).as_posix(),
        "snippet": snippet,
    }
