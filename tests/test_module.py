import shutil
from pathlib import Path

import pytest

from guardrails.module import create_module
from guardrails.util import GuardrailsError

PACK = Path(__file__).resolve().parents[1] / "pack"


def _project(tmp_path: Path, module_root: str = "modules") -> tuple[Path, dict]:
    target = tmp_path / module_root / "_template"
    shutil.copytree(PACK / "modules" / "_template", target)
    return tmp_path, {"project": {"name": "app", "module_root": module_root}}


def test_create_module_from_default_root(tmp_path):
    root, config = _project(tmp_path)
    result = create_module(root, config, "order")
    module = root / "modules" / "order"
    assert result["path"] == "modules/order"
    assert (module / "MODULE.md").exists()
    assert "order" in (module / "MODULE.md").read_text(encoding="utf-8")
    assert "<name>" not in (module / "CONTRACT.md").read_text(encoding="utf-8")
    assert result["snippet"]["contract"] == "modules/order/CONTRACT.md"
    assert "public_path" not in result["snippet"]


def test_create_module_custom_root(tmp_path):
    root, config = _project(tmp_path, module_root="src/features")
    result = create_module(root, config, "billing")
    assert (root / "src" / "features" / "billing" / "MODULE.md").exists()
    assert result["path"] == "src/features/billing"


def test_create_module_detects_public_path(tmp_path):
    root, config = _project(tmp_path)
    (root / "modules" / "_template" / "CONTRACT.ts").write_text("export {};\n", encoding="utf-8")
    result = create_module(root, config, "order")
    assert result["snippet"]["public_path"] == "modules/order/CONTRACT.ts"


def test_create_module_rejects_existing(tmp_path):
    root, config = _project(tmp_path)
    create_module(root, config, "order")
    with pytest.raises(GuardrailsError):
        create_module(root, config, "order")


def test_create_module_rejects_bad_name(tmp_path):
    root, config = _project(tmp_path)
    with pytest.raises(GuardrailsError):
        create_module(root, config, "Order Service")
