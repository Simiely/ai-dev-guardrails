from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from .util import GuardrailsError, normalize_path


def run_mutation(
    root: Path,
    config: dict[str, Any],
    files: list[str],
) -> dict[str, Any]:
    command = str(config.get("commands", {}).get("mutation", "")).strip()
    if not command or "TODO" in command or "<command>" in command:
        return {
            "ran": False,
            "reason": "commands.mutation is not configured",
            "hint": (
                "set commands.mutation in guardrails.yaml, e.g. "
                "\"npx stryker run --incremental\" or \"mutmut run\". "
                "The changed files are in GUARDRAILS_CHANGED_FILES."
            ),
            "exit_code": None,
            "files": [],
        }
    changed = [normalize_path(item) for item in files if item]
    env = os.environ.copy()
    env["GUARDRAILS_CHANGED_FILES"] = ",".join(changed)
    proc = subprocess.run(command, shell=True, cwd=root, env=env)
    return {
        "ran": True,
        "command": command,
        "files": changed,
        "exit_code": proc.returncode,
    }
