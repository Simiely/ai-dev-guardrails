from __future__ import annotations

import shutil
from pathlib import Path

from .util import GuardrailsError


def default_source() -> Path:
    return Path(__file__).resolve().parents[2] / "pack"


def init_project(target: Path, source: Path | None = None, force: bool = False) -> Path:
    source = source or default_source()
    if not source.exists():
        raise GuardrailsError(f"missing pack source: {source}")
    if target.exists() and any(target.iterdir()) and not force:
        raise GuardrailsError(f"target is not empty: {target}; use --force to overwrite")
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True)
    return target


def next_steps(target: Path) -> str:
    return (
        f"initialized {target}\n"
        "next:\n"
        "  1. edit guardrails.yaml (modules, contracts, risk, commands)\n"
        "  2. edit manual/00-card.md and manual/chapters/*/SKILL.md\n"
        "  3. run: guardrails lint-manual\n"
        "  4. run: guardrails sync\n"
        "  5. run: guardrails doctor\n"
    )
