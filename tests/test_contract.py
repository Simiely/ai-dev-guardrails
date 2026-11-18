from guardrails.contract import diff_documents

BASE = {
    "openapi": "3.0.0",
    "paths": {
        "/orders": {
            "get": {
                "responses": {"200": {"description": "ok"}},
            }
        }
    },
    "components": {
        "schemas": {
            "Order": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    "status": {"type": "string", "enum": ["open", "closed"]},
                },
            }
        }
    },
}

CURRENT = {
    "openapi": "3.0.0",
    "paths": {},
    "components": {
        "schemas": {
            "Order": {
                "type": "object",
                "required": ["id", "total"],
                "properties": {
                    "status": {"type": "string", "enum": ["open"]},
                },
            }
        }
    },
}


def test_contract_diff_detects_breaking_changes():
    result = diff_documents(BASE, CURRENT)
    kinds = {change["kind"] for change in result["breaking"]}
    assert "removed" in kinds
    assert "required_added" in kinds
    assert "enum_narrowed" in kinds
    assert result["summary"]["breaking"] >= 3


def test_contract_diff_allows_additive_changes():
    current = {
        **BASE,
        "components": {
            "schemas": {
                "Order": {
                    **BASE["components"]["schemas"]["Order"],
                    "properties": {
                        **BASE["components"]["schemas"]["Order"]["properties"],
                        "note": {"type": "string"},
                    },
                }
            }
        },
    }
    result = diff_documents(BASE, current)
    assert result["summary"]["breaking"] == 0
    assert result["summary"]["non_breaking"] >= 1
