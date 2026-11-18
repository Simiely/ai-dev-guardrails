from guardrails.assets import asset_path
from guardrails.config import repo_schema


def test_assets_resolve_in_source_tree():
    assert (asset_path("pack") / "guardrails.yaml").exists()
    assert (asset_path("schema") / "guardrails.schema.json").exists()


def test_repo_schema_is_available():
    schema = repo_schema("guardrails.schema.json")
    assert schema is not None
    assert schema.exists()
