from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .util import GuardrailsError, load_yaml, read_text, sha256_text, write_text

BASELINE_PATH = ".guardrails/canary-baseline.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_canary(
    root: Path,
    suite_path: Path,
    update_baseline: bool = False,
) -> dict[str, Any]:
    if not suite_path.exists():
        raise GuardrailsError(f"missing canary suite: {suite_path}")
    data = load_yaml(suite_path)
    commands = data.get("commands", [])
    if not commands:
        raise GuardrailsError(f"{suite_path}: no commands")

    current_commands = []
    for item in commands:
        command = str(item.get("run", ""))
        command_id = str(item.get("id") or command)
        if not command:
            continue
        started = time.monotonic()
        proc = subprocess.run(command, shell=True, cwd=root, capture_output=True, text=True)
        duration = round(time.monotonic() - started, 3)
        current_commands.append(
            {
                "id": command_id,
                "run": command,
                "exit_code": proc.returncode,
                "duration": duration,
                "output_hash": sha256_text(proc.stdout + proc.stderr)[:16],
            }
        )

    current = {
        "name": str(data.get("name") or "canary"),
        "timestamp": _now(),
        "commands": current_commands,
    }
    baseline_path = root / BASELINE_PATH
    had_baseline = baseline_path.exists()
    if update_baseline or not had_baseline:
        write_text(baseline_path, json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True))
        return {
            "ok": True,
            "updated": True,
            "created_baseline": not had_baseline,
            "current": current,
            "regressions": [],
            "changed": [],
        }

    baseline = json.loads(read_text(baseline_path))
    base_by_id = {item["id"]: item for item in baseline.get("commands", [])}
    regressions = []
    changed = []
    new_commands = []
    for item in current_commands:
        base = base_by_id.get(item["id"])
        if base is None:
            new_commands.append(item["id"])
            continue
        if base.get("exit_code") == 0 and item["exit_code"] != 0:
            regressions.append(
                {
                    "id": item["id"],
                    "baseline_exit": base.get("exit_code"),
                    "current_exit": item["exit_code"],
                }
            )
        if base.get("output_hash") != item.get("output_hash"):
            changed.append({"id": item["id"]})

    ok = all(item["exit_code"] == 0 for item in current_commands) and not regressions
    return {
        "ok": ok,
        "updated": False,
        "baseline": str(baseline_path),
        "current": current,
        "regressions": regressions,
        "changed": changed,
        "new_commands": new_commands,
    }


def render_canary(result: dict[str, Any]) -> str:
    lines = [f"CANARY: {'PASS' if result['ok'] else 'FAIL'}"]
    if result.get("updated"):
        lines.append(f"- baseline updated: {result.get('baseline', BASELINE_PATH)}")
    for item in result["current"]["commands"]:
        lines.append(
            f"- {item['id']}: exit={item['exit_code']} duration={item['duration']}s hash={item['output_hash']}"
        )
    for item in result.get("regressions", []):
        lines.append(f"- regression: {item['id']} ({item['baseline_exit']} -> {item['current_exit']})")
    for item in result.get("changed", []):
        lines.append(f"- output changed: {item['id']}")
    for item in result.get("new_commands", []):
        lines.append(f"- new command: {item}")
    return "\n".join(lines)
