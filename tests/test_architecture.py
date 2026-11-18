from guardrails.architecture import (
    render_dependency_cruiser,
    render_importlinter,
)

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


def test_importlinter_orders_layers_high_to_low():
    text = render_importlinter(CONFIG)
    assert 'root_packages = ["shop"]' in text
    assert 'layers = ["shop.adapter", "shop.application", "shop.domain"]' in text
