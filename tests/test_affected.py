from pathlib import Path

from guardrails.graph import affected_tests

PY_ROOT = Path(__file__).resolve().parent / "fixtures" / "graph_py"
TS_ROOT = Path(__file__).resolve().parent / "fixtures" / "graph_ts"
CONFIG = {"modules": [], "contracts": []}


def test_python_change_affects_direct_test():
    result = affected_tests(PY_ROOT, CONFIG, ["app/order.py"])
    assert "tests/test_order.py" in result["affected_tests"]
    assert "tests/test_payment.py" not in result["affected_tests"]


def test_python_change_affects_dependent_tests():
    result = affected_tests(PY_ROOT, CONFIG, ["app/payment.py"])
    assert "tests/test_payment.py" in result["affected_tests"]
    assert "tests/test_order.py" in result["affected_tests"]


def test_typescript_change_affects_direct_test():
    result = affected_tests(TS_ROOT, CONFIG, ["src/payment.ts"])
    assert "src/payment.test.ts" in result["affected_tests"]


def test_typescript_change_affects_dependent_test():
    result = affected_tests(TS_ROOT, CONFIG, ["src/payment.ts"])
    assert "src/order.test.ts" in result["affected_tests"]


def test_contract_change_runs_all_tests():
    config = {
        "modules": [],
        "contracts": [{"id": "http.order", "path": "openapi/order.yaml", "kind": "openapi"}],
    }
    result = affected_tests(PY_ROOT, config, ["openapi/order.yaml"])
    assert result["fallback"] == "contract"
    assert set(result["affected_tests"]) == {"tests/test_order.py", "tests/test_payment.py"}
