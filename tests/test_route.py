from pathlib import Path

from guardrails.config import load_config
from guardrails.eval_routing import evaluate_routing
from guardrails.manual import load_chapters
from guardrails.route import load_task, select_chapters

PACK = Path(__file__).resolve().parents[1] / "pack"
SUITE = PACK / "eval" / "routing"


def _router():
    config = load_config(PACK)
    chapters = load_chapters(PACK, config)
    return config, chapters


def test_feature_r3_selects_change_review_verify():
    config, chapters = _router()
    task = load_task(SUITE / "feature-r3.yaml")
    result = select_chapters(task, config, chapters)
    assert result["selected"] == ["change", "review", "verify"]
    assert result["risk"] == "R3"
    assert result["fallback"] == "none"


def test_feature_unfamiliar_selects_context_change_verify():
    config, chapters = _router()
    task = load_task(SUITE / "feature-unfamiliar.yaml")
    result = select_chapters(task, config, chapters)
    assert result["selected"] == ["context", "change", "verify"]


def test_bugfix_does_not_load_change():
    config, chapters = _router()
    task = load_task(SUITE / "bugfix.yaml")
    result = select_chapters(task, config, chapters)
    assert result["selected"] == ["tdd", "verify"]


def test_unknown_type_falls_back_to_intake():
    config, chapters = _router()
    task = load_task(SUITE / "unknown.yaml")
    result = select_chapters(task, config, chapters)
    assert result["selected"] == ["intake", "verify"]


def test_routing_suite_passes():
    config, chapters = _router()
    result = evaluate_routing(PACK, config, chapters, SUITE)
    assert result["passed"] is True
    assert result["recall"] == 1.0
    assert result["zero_load"] == 0.0
    assert all(case["missing"] == [] for case in result["cases"])
