from pathlib import Path

from guardrails.cli import main
from guardrails.hook import evaluate_pre_tool

PACK = Path(__file__).resolve().parents[1] / "pack"
CONFIG = {"protected": ["ARCHITECTURE.md", "manual/**", "adr/**"]}


def test_protected_path_is_denied():
    result = evaluate_pre_tool(
        Path("."),
        CONFIG,
        {"tool_name": "Edit", "tool_input": {"file_path": "manual/00-card.md"}},
    )
    assert result["decision"] == "deny"
    assert "protected path" in result["reason"]


def test_normal_path_is_allowed():
    result = evaluate_pre_tool(
        Path("."),
        CONFIG,
        {"tool_name": "Edit", "tool_input": {"file_path": "modules/order/src/cancel.ts"}},
    )
    assert result["decision"] == "allow"


def test_dangerous_shell_is_denied():
    result = evaluate_pre_tool(
        Path("."),
        CONFIG,
        {"tool_name": "Bash", "tool_input": {"command": "rm -rf /tmp/work"}},
    )
    assert result["decision"] == "deny"


def test_safe_shell_is_allowed():
    result = evaluate_pre_tool(
        Path("."),
        CONFIG,
        {"tool_name": "Bash", "tool_input": {"command": "npm test"}},
    )
    assert result["decision"] == "allow"


def test_cli_hook_blocks_protected_file(capsys):
    payload = '{"tool_name":"Edit","tool_input":{"file_path":"ARCHITECTURE.md"}}'
    assert main(["--root", str(PACK), "hook", "--event", "pre-tool", "--payload", payload]) == 2
    assert "protected path" in capsys.readouterr().err


def test_cli_hook_session_start(capsys):
    assert main(["--root", str(PACK), "hook", "--event", "session-start"]) == 0
    assert "guardrails brief" in capsys.readouterr().out
