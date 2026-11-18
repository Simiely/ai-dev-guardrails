from pathlib import Path

from guardrails.report import build_report, render_report

ROOT = Path(__file__).resolve().parent / "fixtures" / "graph_py"
CONFIG = {"modules": [], "contracts": []}


def test_report_counts_tests_and_tasks():
    report = build_report(ROOT, CONFIG)
    assert report["tests"] == 2
    assert report["modules"] == 0
    text = render_report(report)
    assert "tests: 2" in text
    assert "PR/DORA" in text
