from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_config
from .lint import lint_manual
from .manual import load_card, load_chapters
from .sync import sync_views
from .util import GuardrailsError


def _check(checks: list[dict[str, str]], status: str, name: str, detail: str) -> None:
    checks.append({"status": status, "name": name, "detail": detail})


def run_doctor(root: Path) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    try:
        config = load_config(root)
        _check(checks, "PASS", "config", "guardrails.yaml is valid")
    except GuardrailsError as exc:
        _check(checks, "FAIL", "config", str(exc))
        return {"passed": False, "checks": checks}

    try:
        card = load_card(root, config)
        chapters = load_chapters(root, config)
    except GuardrailsError as exc:
        _check(checks, "FAIL", "manual", str(exc))
        return {"passed": False, "checks": checks}

    if card.lines <= 80:
        _check(checks, "PASS", "card.size", f"{card.lines} lines")
    else:
        _check(checks, "FAIL", "card.size", f"{card.lines} lines > 80")

    max_chapters = int(config.get("manual", {}).get("max_chapters", 6))
    if 2 <= len(chapters) <= max_chapters:
        _check(checks, "PASS", "chapters.count", f"{len(chapters)} chapters")
    else:
        _check(checks, "FAIL", "chapters.count", f"{len(chapters)} chapters; expected 2..{max_chapters}")

    lint = lint_manual(root, config, card, chapters)
    if lint["errors"]:
        _check(checks, "FAIL", "manual.lint", f"{len(lint['errors'])} errors")
    else:
        _check(checks, "PASS", "manual.lint", "no errors")

    sync = sync_views(root, config, check=True)
    if sync["drift"]:
        _check(checks, "FAIL", "views.sync", f"{len(sync['drift'])} stale generated files")
    else:
        _check(checks, "PASS", "views.sync", "generated views are up to date")

    modules_dir = root / "modules"
    if modules_dir.exists():
        actual = {path.name for path in modules_dir.iterdir() if path.is_dir() and path.name != "_template"}
        configured = {str(module.get("name")) for module in config.get("modules", [])}
        if actual != configured:
            _check(
                checks,
                "FAIL",
                "modules.registry",
                f"modules/ vs guardrails.yaml mismatch: extra={sorted(actual - configured)}, missing={sorted(configured - actual)}",
            )
        else:
            _check(checks, "PASS", "modules.registry", f"{len(actual)} registered modules")

    holdout = config.get("holdout")
    if holdout:
        path = root / str(holdout)
        _check(
            checks,
            "PASS" if path.exists() else "FAIL",
            "holdout",
            str(holdout) if path.exists() else f"missing holdout directory: {holdout}",
        )

    languages = [str(item) for item in config.get("project", {}).get("languages", [])]
    if any(item in {"typescript", "javascript"} for item in languages):
        path = root / ".guardrails" / "dependency-cruiser.js"
        _check(
            checks,
            "PASS" if path.exists() else "FAIL",
            "architecture.typescript",
            "generated" if path.exists() else "run guardrails sync",
        )
    if "python" in languages:
        path = root / ".guardrails" / "importlinter.toml"
        _check(
            checks,
            "PASS" if path.exists() else "FAIL",
            "architecture.python",
            "generated" if path.exists() else "run guardrails sync",
        )

    for name in ("affected", "full", "typecheck", "lint"):
        value = str(config.get("commands", {}).get(name, ""))
        if not value or "TODO" in value or "<command>" in value:
            _check(checks, "FAIL", f"command.{name}", "set a real command in guardrails.yaml")
        else:
            _check(checks, "PASS", f"command.{name}", value)

    workflow = root / ".github" / "workflows"
    has_ci = any(workflow.glob("*.yml")) or (root / "ci" / "gates.yml").exists() or (root / "pack" / "ci" / "gates.yml").exists()
    _check(checks, "PASS" if has_ci else "WARN", "ci", "workflow found" if has_ci else "no workflow found")

    settings = root / ".claude" / "settings.json"
    if settings.exists():
        text = settings.read_text(encoding="utf-8")
        if "guardrails hook" in text:
            _check(checks, "PASS", "hooks", "Claude Code hook references guardrails")
        else:
            _check(checks, "WARN", "hooks", "settings.json exists but does not call guardrails hook")
    else:
        _check(checks, "WARN", "hooks", "no .claude/settings.json; runtime protections are not installed")

    passed = all(check["status"] != "FAIL" for check in checks)
    return {"passed": passed, "checks": checks}
