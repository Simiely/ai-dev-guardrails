import shutil
from pathlib import Path

from guardrails.state import (
    active_task,
    handoff_text,
    init_state,
    load_state,
    set_active,
    update_state,
)

PACK = Path(__file__).resolve().parents[1] / "pack"


def _task_file(root: Path) -> Path:
    path = root / "specs" / "t1" / "task.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "id: t1\ntype: feature\nfiles: [app/a.py]\ngoal: do it\nrisk: R2\n",
        encoding="utf-8",
    )
    return path


def test_init_and_update_state(tmp_path):
    task_file = _task_file(tmp_path)
    data = init_state(tmp_path, "t1", task_file)
    assert data["type"] == "feature"
    assert data["risk"] == "R2"
    assert data["goal"] == "do it"

    update_state(tmp_path, "t1", next="implement", chapter="change")
    saved = load_state(tmp_path, "t1")
    assert saved["next"] == "implement"
    assert saved["chapter"] == "change"


def test_active_task(tmp_path):
    set_active(tmp_path, "t1")
    assert active_task(tmp_path) == "t1"


def test_handoff_without_manual_is_safe(tmp_path):
    _task_file(tmp_path)
    init_state(tmp_path, "t1")
    text = handoff_text(tmp_path, "t1")
    assert "# Handoff: t1" in text
    assert "manual/card not available" in text


def test_handoff_includes_card_and_chapter(tmp_path):
    project = tmp_path / "project"
    shutil.copytree(PACK, project)
    task_file = _task_file(project)
    init_state(project, "t1", task_file)
    update_state(project, "t1", chapter="change")
    text = handoff_text(project, "t1")
    assert "项目说明书" in text
    assert "规格与计划" in text


def test_handoff_includes_raw_and_trace(tmp_path):
    project = tmp_path / "project"
    shutil.copytree(PACK, project)
    task_file = _task_file(project)
    init_state(project, "t1", task_file)
    raw = project / "specs" / "t1" / "raw"
    raw.mkdir()
    (raw / "manifest.json").write_text('{"sources": []}', encoding="utf-8")
    (project / "specs" / "t1" / "trace.yaml").write_text("claims: []\n", encoding="utf-8")
    text = handoff_text(project, "t1")
    assert "## Raw Sources" in text
    assert "## Trace" in text
    assert "verify-trace --task t1" in text
