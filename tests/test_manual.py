from pathlib import Path

from guardrails.config import load_config
from guardrails.lint import lint_manual
from guardrails.manual import load_manual

PACK = Path(__file__).resolve().parents[1] / "pack"


def test_pack_manual_lints_clean():
    config = load_config(PACK)
    card, chapters = load_manual(PACK, config)
    result = lint_manual(PACK, config, card, chapters)
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["chapters"] == 6
    assert result["card_lines"] <= 80


def test_every_chapter_has_when_and_when_not():
    config = load_config(PACK)
    _, chapters = load_manual(PACK, config)
    for chapter in chapters:
        assert chapter.when_to_use
        assert chapter.when_not_to_use
        assert "用于" in chapter.description or "当" in chapter.description
        assert "不要" in chapter.description or "不在" in chapter.description
