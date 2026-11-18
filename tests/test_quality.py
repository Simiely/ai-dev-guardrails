from pathlib import Path

from guardrails.quality import quality_report

ROOT = Path(__file__).resolve().parent / "fixtures" / "quality"


def test_long_complex_function_is_flagged():
    result = quality_report(ROOT, ["app/bad.py"])
    kinds = {item["kind"] for item in result["violations"]}
    assert "function_too_long" in kinds
    assert "complexity_too_high" in kinds


def test_small_function_is_clean():
    result = quality_report(ROOT, ["app/ok.py"])
    assert result["violations"] == []


def test_duplicate_block_is_detected():
    result = quality_report(ROOT, ["app/dup_a.py"])
    assert result["duplicates"]
    locations = result["duplicates"][0]["locations"]
    files = {item["file"] for item in locations}
    assert "app/dup_a.py" in files
    assert "app/dup_b.py" in files
