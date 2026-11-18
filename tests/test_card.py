from pathlib import Path

from guardrails.card import build_card

ROOT = Path(__file__).resolve().parent / "fixtures" / "graph_py"
CONFIG = {"modules": [], "contracts": []}


def test_card_contains_risk_tests_and_rollback():
    result = build_card(ROOT, CONFIG, ROOT / "task.yaml")
    assert result["task"] == "change-order"
    assert result["risk"] == "R1"
    assert "tests/test_order.py" in result["affected_tests"]
    assert "后果卡" in result["markdown"]
    assert "回滚" in result["markdown"]
