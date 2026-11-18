import json
from pathlib import Path

from guardrails.custody import (
    LEGACY_LOCK_PATH,
    approve_tests,
    check_tests,
    lock_path,
    lock_tests,
    locked_test_for,
)
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
    data = json.loads(lock_path(root, "t1").read_text(encoding="utf-8"))
    assert "acceptance/holdout/test_h.py" in data["files"]


def test_two_tasks_keep_separate_locks(tmp_path):
    root = _project(tmp_path)
    lock_tests(root, CONFIG, "t1")
    lock_tests(root, CONFIG, "t2")
    assert check_tests(root, "t1")["ok"] is True
    assert check_tests(root, "t2")["ok"] is True
    assert lock_path(root, "t1").exists()
    assert lock_path(root, "t2").exists()
    assert locked_test_for(root, "tests/test_a.py") == "t1"


def test_legacy_lock_for_other_task_is_ignored(tmp_path):
    root = _project(tmp_path)
    legacy = root / LEGACY_LOCK_PATH
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(
        json.dumps({"task": "old", "files": {"tests/test_a.py": "sha256:deadbeef"}}),
        encoding="utf-8",
    )
    result = check_tests(root, "new")
    assert result["locked"] is False
    assert result["ok"] is True
    assert result["legacy_task"] == "old"


def test_hook_requires_approval_for_every_locking_task(tmp_path):
    root = _project(tmp_path)
    lock_tests(root, CONFIG, "t1")
    lock_tests(root, CONFIG, "t2")
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "tests/test_a.py"}}

    denied = evaluate_pre_tool(root, {"protected": []}, payload)
    assert denied["decision"] == "deny"

    approve_tests(root, "t1", "intentional")
    still_denied = evaluate_pre_tool(root, {"protected": []}, payload)
    assert still_denied["decision"] == "deny"

    approve_tests(root, "t2", "intentional")
    allowed = evaluate_pre_tool(root, {"protected": []}, payload)
    assert allowed["decision"] == "allow"
