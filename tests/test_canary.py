import json
from pathlib import Path

from guardrails.canary import run_canary


def _suite(root: Path, command: str) -> Path:
    path = root / "eval" / "canary.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "name: test\ncommands:\n  - id: check\n    run: " + json.dumps(command) + "\n",
        encoding="utf-8",
    )
    return path


def test_canary_creates_baseline_then_passes(tmp_path):
    suite = _suite(tmp_path, "python -c \"print('ok')\"")
    first = run_canary(tmp_path, suite)
    assert first["updated"] is True
    second = run_canary(tmp_path, suite)
    assert second["ok"] is True
    assert second["regressions"] == []


def test_canary_detects_regression(tmp_path):
    passing = _suite(tmp_path, "python -c \"print('ok')\"")
    run_canary(tmp_path, passing)
    failing = _suite(tmp_path, "python -c \"import sys; sys.exit(1)\"")
    result = run_canary(tmp_path, failing)
    assert result["ok"] is False
    assert result["regressions"][0]["id"] == "check"
