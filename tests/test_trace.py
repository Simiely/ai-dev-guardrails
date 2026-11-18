import hashlib
import json
from pathlib import Path

import pytest

from guardrails.trace import add_raw_source, raw_sources, verify_trace
from guardrails.util import GuardrailsError


def _write_raw(root: Path, text: str = "原始需求\n") -> tuple[Path, str]:
    raw = root / "specs" / "t1" / "raw"
    raw.mkdir(parents=True)
    path = raw / "request.md"
    path.write_text(text, encoding="utf-8")
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "task": "t1",
        "captured_at": "2026-11-18T12:00:00+08:00",
        "sources": [{"path": "raw/request.md", "origin": "issue #1", "sha256": digest}],
    }
    (raw / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return path, digest


def _trace(root: Path, content: str) -> None:
    path = root / "specs" / "t1" / "trace.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_trace_passes_for_matching_raw(tmp_path):
    _, digest = _write_raw(tmp_path)
    _trace(
        tmp_path,
        f"""claims:
  - id: C1
    claim: 取消后不自动退款
    source: raw/request.md
    lines: "1-1"
    sha256: "{digest}"
""",
    )
    result = verify_trace(tmp_path, task="t1")
    assert result["ok"] is True, result
    assert result["errors"] == []


def test_trace_fails_on_stale_hash(tmp_path):
    _write_raw(tmp_path)
    _trace(
        tmp_path,
        """claims:
  - id: C1
    claim: 取消后不自动退款
    source: raw/request.md
    sha256: "sha256:deadbeef"
""",
    )
    result = verify_trace(tmp_path, task="t1")
    assert result["ok"] is False
    assert any("sha256 mismatch" in item for item in result["errors"]), result


def test_trace_missing_source_fails(tmp_path):
    _trace(
        tmp_path,
        """claims:
  - id: C1
    claim: 不存在
    source: raw/nope.md
""",
    )
    result = verify_trace(tmp_path, task="t1")
    assert result["ok"] is False
    assert any("source not found" in item for item in result["errors"])


def test_trace_claim_without_source_is_warning(tmp_path):
    _trace(
        tmp_path,
        """claims:
  - id: C1
    claim: 未验证的假设
""",
    )
    assert verify_trace(tmp_path, task="t1")["ok"] is True
    assert verify_trace(tmp_path, task="t1")["warnings"]
    assert verify_trace(tmp_path, task="t1", require_sources=True)["ok"] is False


def test_trace_acceptance_warns_on_missing_test(tmp_path):
    _trace(
        tmp_path,
        """acceptance:
  - criterion: 用户可以取消订单
""",
    )
    result = verify_trace(tmp_path, task="t1")
    assert result["ok"] is True
    assert any("missing test" in item for item in result["warnings"])


def test_trace_all_with_no_files_passes(tmp_path):
    result = verify_trace(tmp_path, all_tasks=True)
    assert result["ok"] is True
    assert result["checked"] == 0


def test_raw_sources_reads_manifest(tmp_path):
    _write_raw(tmp_path)
    sources = raw_sources(tmp_path, "t1")
    assert sources and sources[0]["path"] == "raw/request.md"


def test_add_raw_source_records_manifest(tmp_path):
    source = tmp_path / "issue.md"
    source.write_text("原始需求\n", encoding="utf-8")
    entry = add_raw_source(tmp_path, "t1", source, origin="issue #1")
    assert entry["path"] == "raw/issue.md"
    assert entry["sha256"].startswith("sha256:")
    assert (tmp_path / "specs" / "t1" / "raw" / "issue.md").exists()
    assert raw_sources(tmp_path, "t1")[0]["origin"] == "issue #1"


def test_add_raw_source_refuses_overwrite(tmp_path):
    source = tmp_path / "issue.md"
    source.write_text("原始需求\n", encoding="utf-8")
    add_raw_source(tmp_path, "t1", source)
    with pytest.raises(GuardrailsError):
        add_raw_source(tmp_path, "t1", source)
