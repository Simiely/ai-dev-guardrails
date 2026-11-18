from guardrails.risk import classify

CONFIG = {
    "risk": {"R3": ["openapi/**", "migrations/**"], "R2": ["modules/**"]},
    "modules": [
        {"name": "order", "path": "modules/order"},
        {"name": "payment", "path": "modules/payment"},
    ],
    "contracts": [],
}


def test_docs_is_r0():
    assert classify(["docs/readme.md"], CONFIG)["level"] == "R0"


def test_single_module_is_r1():
    assert classify(["modules/order/src/cancel.ts"], CONFIG)["level"] == "R1"


def test_two_modules_is_r2():
    result = classify(
        ["modules/order/src/cancel.ts", "modules/payment/src/refund.ts"],
        CONFIG,
    )
    assert result["level"] == "R2"
    assert set(result["modules"]) == {"order", "payment"}


def test_openapi_is_r3():
    result = classify(["openapi/order.yaml"], CONFIG)
    assert result["level"] == "R3"
    assert any("R3 path" in reason for reason in result["reasons"])


def test_unknown_default_is_configurable():
    config = {**CONFIG, "risk": {**CONFIG["risk"], "unknown_default": "R2"}}
    result = classify(["src/unknown.py"], config)
    assert result["level"] == "R2"
    assert any("default R2" in reason for reason in result["reasons"])


def test_unknown_default_invalid_falls_back_to_r1():
    config = {**CONFIG, "risk": {**CONFIG["risk"], "unknown_default": "R9"}}
    assert classify(["src/unknown.py"], config)["level"] == "R1"
