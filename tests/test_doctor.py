import shutil
from pathlib import Path

import yaml

from guardrails.config import load_config
from guardrails.doctor import run_doctor
from guardrails.sync import sync_views

PACK = Path(__file__).resolve().parents[1] / "pack"


def _ready_project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    shutil.copytree(PACK, project)
    config_path = project / "guardrails.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["modules"] = [
        {
            "name": "order",
            "path": "modules/order",
            "layer": "application",
            "contract": "modules/order/CONTRACT.md",
            "public_path": "modules/order/CONTRACT.ts",
        }
    ]
    config["commands"] = {
        "affected": "python -c \"pass\"",
        "full": "python -c \"pass\"",
        "typecheck": "python -c \"pass\"",
        "lint": "python -c \"pass\"",
    }
    config_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    sync_views(project, load_config(project), check=False)
    module = project / "modules" / "order"
    module.mkdir(parents=True)
    (module / "CONTRACT.md").write_text("# contract\n", encoding="utf-8")
    (module / "CONTRACT.ts").write_text("export {};\n", encoding="utf-8")
    return project, config_path


def _checks(result):
    return {item["name"]: item for item in result["checks"]}


def test_doctor_passes_for_valid_modules(tmp_path):
    project, _ = _ready_project(tmp_path)
    result = run_doctor(project)
    assert result["passed"] is True, result


def test_doctor_fails_for_missing_module_path(tmp_path):
    project, config_path = _ready_project(tmp_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["modules"][0]["path"] = "modules/missing"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    result = run_doctor(project)
    assert _checks(result)["modules.paths"]["status"] == "FAIL"


def test_doctor_fails_for_missing_public_path(tmp_path):
    project, config_path = _ready_project(tmp_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["modules"][0]["public_path"] = "modules/order/NOPE.ts"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    result = run_doctor(project)
    assert _checks(result)["modules.files"]["status"] == "FAIL"


def test_doctor_fails_for_unknown_layer(tmp_path):
    project, config_path = _ready_project(tmp_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["modules"][0]["layer"] = "nope"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    result = run_doctor(project)
    assert _checks(result)["modules.layers"]["status"] == "FAIL"


def test_doctor_fails_for_unknown_python_layer_package(tmp_path):
    project, config_path = _ready_project(tmp_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["project"]["python"] = {
        "root_package": "app",
        "layer_packages": {"nope": "app.nope"},
    }
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    result = run_doctor(project)
    assert _checks(result)["python.layer_packages"]["status"] == "FAIL"
