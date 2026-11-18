from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Iterator

from .assets import asset_path
from .util import GuardrailsError

IGNORED_ROOT_NAMES = {".git", ".gitignore", "README.md", ".DS_Store"}

# Brownfield projects already have their own code, docs and agent files.
# Copy only the contract/manual layer; never touch their modules or adapters.
BROWNFIELD_PATHS = (
    "guardrails.yaml",
    "manual",
    "templates",
    "specs",
    "acceptance",
    "ci",
    "eval",
    "lessons.md",
    "ARCHITECTURE.md",
    "modules/_template",
)


def default_source() -> Path:
    return asset_path("pack")


def _planned_entries(source: Path, mode: str) -> Iterator[tuple[Path, Path]]:
    if mode == "greenfield":
        for path in sorted(source.rglob("*")):
            if path.is_file():
                yield path, path.relative_to(source)
        return
    if mode != "brownfield":
        raise GuardrailsError(f"unknown init mode: {mode!r}; use greenfield or brownfield")
    for relative in BROWNFIELD_PATHS:
        path = source / relative
        if path.is_file():
            yield path, Path(relative)
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    yield child, child.relative_to(source)


def init_project(
    target: Path,
    source: Path | None = None,
    force: bool = False,
    mode: str = "greenfield",
    dry_run: bool = False,
) -> dict[str, Any]:
    source = source or default_source()
    if mode not in {"greenfield", "brownfield"}:
        raise GuardrailsError(f"unknown init mode: {mode!r}; use greenfield or brownfield")
    if not source.exists():
        raise GuardrailsError(f"missing pack source: {source}")

    if target.exists() and mode == "greenfield" and not force:
        existing = [path for path in target.iterdir() if path.name not in IGNORED_ROOT_NAMES]
        if existing:
            names = ", ".join(sorted(path.name for path in existing))
            raise GuardrailsError(
                f"target is not empty: {target} ({names}); "
                "use --mode brownfield for an existing project, or --force to overwrite"
            )

    planned = list(_planned_entries(source, mode))
    copied: list[str] = []
    skipped: list[str] = []
    conflicts: list[str] = []

    for src, relative in planned:
        dest = target / relative
        if dest.exists():
            if dest.is_file() and dest.read_bytes() == src.read_bytes():
                skipped.append(str(relative))
                continue
            if not force:
                conflicts.append(str(relative))
                skipped.append(str(relative))
                continue
        copied.append(str(relative))
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)

    return {
        "target": str(target),
        "mode": mode,
        "copied": copied,
        "skipped": skipped,
        "conflicts": conflicts,
        "dry_run": dry_run,
    }


def next_steps(result: dict[str, Any]) -> str:
    target = result["target"]
    lines = [
        f"initialized {target} ({result['mode']})",
        f"copied: {len(result['copied'])}, skipped: {len(result['skipped'])}",
    ]
    if result["dry_run"]:
        lines.append("dry-run: no files written")
    if result["conflicts"]:
        lines.append("conflicts (existing files kept, not overwritten):")
        for path in result["conflicts"]:
            lines.append(f"  - {path}")
        lines.append("merge them manually, or rerun with --force if you intend to overwrite.")
    lines += [
        "next:",
        "  1. edit guardrails.yaml (modules, contracts, risk, commands)",
        "  2. edit manual/00-card.md and manual/chapters/*/SKILL.md",
        "  3. run: guardrails lint-manual",
        "  4. run: guardrails sync",
        "  5. run: guardrails doctor",
    ]
    return "\n".join(lines)
