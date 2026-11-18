import json
from pathlib import Path

from guardrails.custody import LOCK_PATH, approve_tests, check_tests, lock_tests
from guardrails.hook import evaluate_pre_tool

CONFIG = {"modules": [], "contracts": []}


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "tests").mkdir(parents=True)
    (root / "app").mkdir()
    (root / "app" / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (root / "tests" / "test_a.py").write_text(
        "from app.a import f\n\ndef test_f():\n    assert f() == 1\n",
        encoding="utf-8",
    )
    return root


def test_lock_then_check_passes(tmp_path):
    root = _project(tmp_path)
    result = lock_tests(root, CONFIG, "t1")
    assert result["locked"] == 1
    assert check_tests(root, "t1")["ok"] is True


def test_modified_test_fails_check(tmp_path):
    root = _project(tmp_path)
    lock_tests(root, CONFIG, "t1")
    (root / "tests" / "test_a.py").write_text(
        "from app.a import f\n\ndef test_f():\n    assert f() == 2\n",
        encoding="utf-8",
    )
    result = check_tests(root, "t1")
    assert result["ok"] is False
    assert result["changed"] == ["tests/test_a.py"]


def test_hook_blocks_locked_test_until_approved(tmp_path):
    root = _project(tmp_path)
    lock_tests(root, CONFIG, "t1")
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "tests/test_a.py"}}
    denied = evaluate_pre_tool(root, {"protected": []}, payload)
    assert denied["decision"] == "deny"

    approve_tests(root, "t1", "intentional oracle update")
    allowed = evaluate_pre_tool(root, {"protected": []}, payload)
    assert allowed["decision"] == "allow"


def test_approved_edit_requires_relock(tmp_path):
    root = _project(tmp_path)
    lock_tests(root, CONFIG, "t1")
    (root / "tests" / "test_a.py").write_text(
        "from app.a import f\n\ndef test_f():\n    assert f() == 2\n",
        encoding="utf-8",
    )
    approve_tests(root, "t1", "intentional oracle update")
    result = check_tests(root, "t1")
    assert result["ok"] is False
    assert result["approved"] is True
    assert result["needs_relock"] is True

    lock_tests(root, CONFIG, "t1")
    assert check_tests(root, "t1")["ok"] is True


def test_holdout_tests_are_locked(tmp_path):
    root = _project(tmp_path)
    holdout = root / "acceptance" / "holdout"
    holdout.mkdir(parents=True)
    (holdout / "test_h.py").write_text("def test_h():\n    assert True\n", encoding="utf-8")
    config = {**CONFIG, "holdout": "acceptance/holdout"}
    lock_tests(root, config, "t1")
    data = json.loads((root / LOCK_PATH).read_text(encoding="utf-8"))
    assert "acceptance/holdout/test_h.py" in data["files"]
