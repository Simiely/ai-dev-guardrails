from pathlib import Path

from guardrails.metrics import ingest_junit, metrics_report, record_run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_metrics_record_and_report(tmp_path):
    record_run(tmp_path, "t1", "pass", tests_total=10, tests_failed=0, duration=1.0)
    record_run(tmp_path, "t2", "fail", tests_total=10, tests_failed=2, duration=2.0, rework=True)
    report = metrics_report(tmp_path)
    assert report["runs"] == 2
    assert report["pass_rate"] == 0.5
    assert report["run_failure_rate"] == 0.5
    assert report["rework_rate"] == 0.5
    assert report["avg_failed_tests"] == 1.0
    assert report["by_task"]["t2"]["runs"] == 1


def test_ingest_junit(tmp_path):
    result = ingest_junit(tmp_path, FIXTURES / "junit.xml", "t1")
    assert result["status"] == "fail"
    assert result["tests_total"] == 3
    assert result["tests_failed"] == 1
    assert metrics_report(tmp_path)["runs"] == 1
