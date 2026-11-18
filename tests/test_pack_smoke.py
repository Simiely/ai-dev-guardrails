from pathlib import Path

import yaml

from guardrails.config import load_config
from guardrails.doctor import run_doctor
from guardrails.init import init_project
from guardrails.manual import load_chapters, load_manual
from guardrails.lint import lint_manual
from guardrails.sync import GENERATED, sync_views

PACK = Path(__file__).resolve().parents[1] / "pack"


def _make_ready_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    init_project(project, source=PACK)
    config_path = project / "guardrails.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["commands"] = {
        "affected": "python -c \"pass\"",
        "full": "python -c \"pass\"",
        "typecheck": "python -c \"pass\"",
        "lint": "python -c \"pass\"",
    }
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    workflow = project / ".github" / "workflows" / "gates.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text("name: gates\non: [push]\njobs: {}\n", encoding="utf-8")
    return project


def test_init_copies_pack(tmp_path):
    project = tmp_path / "project"
    init_project(project, source=PACK)
    assert (project / "guardrails.yaml").exists()
    assert (project / "manual" / "00-card.md").exists()
    assert (project / "manual" / "chapters" / "change" / "SKILL.md").exists()


def test_ready_project_passes_lint_sync_and_doctor(tmp_path):
    project = _make_ready_project(tmp_path)
    config = load_config(project)
    card, chapters = load_manual(project, config)
    assert lint_manual(project, config, card, chapters)["errors"] == []
    assert len(chapters) == 6
    (project / "AGENTS.md").write_text(GENERATED + "\n\n# stale\n", encoding="utf-8")
    assert sync_views(project, config, check=False)["written"]
    assert sync_views(project, config, check=True)["drift"] == []
    result = run_doctor(project)
    assert result["passed"] is True, result
