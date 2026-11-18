from pathlib import Path

import pytest

from guardrails.init import init_project
from guardrails.util import GuardrailsError

PACK = Path(__file__).resolve().parents[1] / "pack"


def test_init_allows_git_dir(tmp_path):
    target = tmp_path / "project"
    (target / ".git").mkdir(parents=True)
    result = init_project(target, source=PACK)
    assert (target / "guardrails.yaml").exists()
    assert (target / "manual" / "00-card.md").exists()
    assert result["mode"] == "greenfield"


def test_init_greenfield_rejects_non_empty(tmp_path):
    target = tmp_path / "project"
    (target / "src").mkdir(parents=True)
    (target / "src" / "app.py").write_text("x", encoding="utf-8")
    with pytest.raises(GuardrailsError):
        init_project(target, source=PACK)


def test_init_brownfield_preserves_existing(tmp_path):
    target = tmp_path / "project"
    (target / "modules" / "order").mkdir(parents=True)
    (target / "modules" / "order" / "app.py").write_text("x", encoding="utf-8")
    (target / "AGENTS.md").write_text("handwritten\n", encoding="utf-8")
    (target / "guardrails.yaml").write_text("custom: true\n", encoding="utf-8")

    result = init_project(target, source=PACK, mode="brownfield")

    assert (target / "AGENTS.md").read_text(encoding="utf-8") == "handwritten\n"
    assert (target / "guardrails.yaml").read_text(encoding="utf-8") == "custom: true\n"
    assert (target / "manual" / "00-card.md").exists()
    assert (target / "modules" / "order" / "app.py").exists()
    assert not (target / "modules" / "order" / "MODULE.md").exists()
    assert "guardrails.yaml" in result["conflicts"]


def test_init_dry_run_writes_nothing(tmp_path):
    target = tmp_path / "project"
    result = init_project(target, source=PACK, dry_run=True)
    assert result["copied"]
    assert not target.exists()


def test_init_force_overwrites(tmp_path):
    target = tmp_path / "project"
    target.mkdir()
    (target / "guardrails.yaml").write_text("old\n", encoding="utf-8")
    result = init_project(target, source=PACK, force=True)
    assert "guardrails.yaml" in result["copied"]
    assert "version: 1" in (target / "guardrails.yaml").read_text(encoding="utf-8")
