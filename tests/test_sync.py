import shutil
from pathlib import Path

from guardrails.config import load_config
from guardrails.sync import GENERATED, sync_views

PACK = Path(__file__).resolve().parents[1] / "pack"


def test_pack_views_are_up_to_date():
    config = load_config(PACK)
    result = sync_views(PACK, config, check=True)
    assert result["drift"] == []
    assert result["conflicts"] == []


def test_sync_rewrites_stale_generated_agents(tmp_path):
    project = tmp_path / "project"
    shutil.copytree(PACK, project)
    agents = project / "AGENTS.md"
    agents.write_text(GENERATED + "\n\n# stale\n", encoding="utf-8")
    config = load_config(project)
    result = sync_views(project, config, check=False)
    assert any(path.endswith("AGENTS.md") for path in result["written"])
    assert "章节索引" in agents.read_text(encoding="utf-8")


def test_sync_check_reports_stale_generated(tmp_path):
    project = tmp_path / "project"
    shutil.copytree(PACK, project)
    agents = project / "AGENTS.md"
    agents.write_text(GENERATED + "\n\n# stale\n", encoding="utf-8")
    config = load_config(project)
    result = sync_views(project, config, check=True)
    assert any(item["path"].endswith("AGENTS.md") for item in result["drift"])


def test_sync_refuses_unmanaged_file(tmp_path):
    project = tmp_path / "project"
    shutil.copytree(PACK, project)
    agents = project / "AGENTS.md"
    agents.write_text("# handwritten\n", encoding="utf-8")
    config = load_config(project)
    result = sync_views(project, config, check=False)
    assert any(item["path"].endswith("AGENTS.md") for item in result["conflicts"])
    assert agents.read_text(encoding="utf-8") == "# handwritten\n"


def test_sync_force_overwrites_unmanaged_file(tmp_path):
    project = tmp_path / "project"
    shutil.copytree(PACK, project)
    agents = project / "AGENTS.md"
    agents.write_text("# handwritten\n", encoding="utf-8")
    config = load_config(project)
    result = sync_views(project, config, check=False, force=True)
    assert any(path.endswith("AGENTS.md") for path in result["written"])
    assert "章节索引" in agents.read_text(encoding="utf-8")


def test_generated_claude_skill_has_name_and_description():
    config = load_config(PACK)
    result = sync_views(PACK, config, check=True)
    assert result["drift"] == []
    skill = PACK / ".claude" / "skills" / "change" / "SKILL.md"
    assert skill.exists()
    text = skill.read_text(encoding="utf-8")
    assert "name: change" in text
    assert "description:" in text


def test_generated_architecture_configs_exist():
    config = load_config(PACK)
    sync_views(PACK, config, check=False)
    assert (PACK / ".guardrails" / "dependency-cruiser.js").exists()
    assert (PACK / ".guardrails" / "importlinter.toml").exists()
    assert (PACK / ".guardrails" / "README.md").exists()
