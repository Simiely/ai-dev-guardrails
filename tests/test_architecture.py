from guardrails.architecture import (
    render_dependency_cruiser,
    render_importlinter,
)
from guardrails.config import load_config

CONFIG = {
    "project": {"name": "shop", "languages": ["typescript", "python"]},
    "layers": ["domain", "application", "adapter"],
    "modules": [
        {"name": "order", "path": "modules/order", "layer": "application"},
        {"name": "payment", "path": "modules/payment", "layer": "domain"},
    ],
}


def test_dependency_cruiser_contains_layer_rules():
    text = render_dependency_cruiser(CONFIG)
    assert "no-domain-to-application" in text
    assert "no-domain-to-adapter" in text
    assert "no-application-to-adapter" in text
    assert "no-cross-module-internal" in text


def test_dependency_cruiser_uses_public_path():
    config = {
        **CONFIG,
        "modules": [
            {
                "name": "order",
                "path": "modules/order",
                "layer": "application",
                "public_path": "modules/order/CONTRACT.ts",
            },
            {
                "name": "payment",
                "path": "modules/payment",
                "layer": "domain",
            },
        ],
    }
    text = render_dependency_cruiser(config)
    assert r"modules/order/CONTRACT\\.ts" in text
    assert "CONTRACT-internal" not in text


def test_dependency_cruiser_default_public_api_is_strict():
    text = render_dependency_cruiser(CONFIG)
    assert "(CONTRACT|index)" in text
    assert 'pathNot: "CONTRACT"' not in text


def test_importlinter_orders_layers_high_to_low():
    text = render_importlinter(CONFIG)
    assert 'root_packages = ["shop"]' in text
    assert 'layers = ["shop.adapter", "shop.application", "shop.domain"]' in text


def test_importlinter_uses_python_layer_packages():
    config = {
        **CONFIG,
        "project": {
            **CONFIG["project"],
            "python": {
                "root_package": "app",
                "layer_packages": {
                    "domain": "app.core.domain",
                    "application": "app.core.application",
                    "adapter": "app.web",
                },
            },
        },
    }
    text = render_importlinter(config)
    assert 'root_packages = ["app"]' in text
    assert 'layers = ["app.web", "app.core.application", "app.core.domain"]' in text


def test_config_accepts_python_layer_packages_and_public_path(tmp_path):
    (tmp_path / "guardrails.yaml").write_text(
        """
version: 1
project:
  name: legacy-app
  languages: [python]
  python:
    root_package: app
    layer_packages:
      domain: app.core.domain
layers: [domain]
modules:
  - name: order
    path: modules/order
    layer: domain
    public_path: modules/order/CONTRACT.ts
contracts: []
manual:
  root: manual
  card: manual/00-card.md
  chapters: manual/chapters
commands:
  affected: "true"
  full: "true"
  typecheck: "true"
  lint: "true"
""",
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    assert config["project"]["python"]["root_package"] == "app"
    assert config["modules"][0]["public_path"] == "modules/order/CONTRACT.ts"
