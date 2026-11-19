import json
import shutil
from pathlib import Path

from guardrails.cli import main

PACK = Path(__file__).resolve().parents[1] / "pack"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_cli_lint_and_sync(capsys):
    assert main(["--root", str(PACK), "lint-manual"]) == 0
    assert main(["--root", str(PACK), "sync", "--check"]) == 0
    output = capsys.readouterr().out
    assert "PASS" in output


def test_cli_brief_json(capsys):
    task = PACK / "eval" / "routing" / "feature-r3.yaml"
    assert main(["--root", str(PACK), "brief", "--task", str(task), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["selected"] == ["change", "review", "verify"]


def test_cli_eval_routing(capsys):
    assert main(["--root", str(PACK), "eval-routing"]) == 0
    output = capsys.readouterr().out
    assert "EVAL ROUTING: PASS" in output


def test_cli_affected_json(capsys):
    root = FIXTURES / "graph_py"
    assert main(["--root", str(root), "affected", "--files", "app/order.py", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["affected_tests"] == ["tests/test_order.py"]


def test_cli_quality_fail_on(capsys):
    root = FIXTURES / "quality"
    assert main(["--root", str(root), "quality", "--files", "app/bad.py"]) == 0
    assert main(["--root", str(root), "quality", "--files", "app/bad.py", "--fail-on"]) == 1
    assert "function_too_long" in capsys.readouterr().out


def test_cli_card(capsys):
    root = FIXTURES / "graph_py"
    assert main(["--root", str(root), "card", "--task", str(root / "task.yaml")]) == 0
    output = capsys.readouterr().out
    assert "后果卡" in output
    assert "tests/test_order.py" in output


def test_cli_state_init_and_handoff(tmp_path, capsys):
    task_file = FIXTURES / "graph_py" / "task.yaml"
    assert main(["--root", str(tmp_path), "state", "init", "--task", "t1", "--task-file", str(task_file)]) == 0
    assert (tmp_path / "specs" / "t1" / "state.json").exists()
    assert main(["--root", str(tmp_path), "state", "handoff", "--task", "t1"]) == 0
    assert "# Handoff: t1" in capsys.readouterr().out


def test_cli_report(capsys):
    root = FIXTURES / "graph_py"
    assert main(["--root", str(root), "report", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["tests"] == 2


def test_cli_task_new(tmp_path, capsys):
    shutil.copytree(PACK / "templates", tmp_path / "templates")
    assert main(["--root", str(tmp_path), "task", "new", "--id", "t1", "--title", "T", "--risk", "R1"]) == 0
    assert (tmp_path / "specs" / "t1" / "task.yaml").exists()
    assert "TASK: t1" in capsys.readouterr().out


def test_cli_module_new(tmp_path, capsys):
    project = tmp_path / "project"
    shutil.copytree(PACK, project)
    assert main(["--root", str(project), "module", "new", "--name", "order", "--layer", "application"]) == 0
    assert (project / "modules" / "order" / "MODULE.md").exists()
    assert "MODULE: order" in capsys.readouterr().out


def test_cli_verify_trace_all_empty(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "verify-trace", "--all"]) == 0
    assert "TRACE: PASS" in capsys.readouterr().out


def test_cli_raw_add_and_list(tmp_path, capsys):
    source = tmp_path / "issue.md"
    source.write_text("原始需求\n", encoding="utf-8")
    assert main([
        "--root", str(tmp_path), "raw", "add",
        "--task", "t1", "--from", str(source), "--origin", "issue #1",
    ]) == 0
    assert (tmp_path / "specs" / "t1" / "raw" / "issue.md").exists()
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "raw", "list", "--task", "t1", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["origin"] == "issue #1"
