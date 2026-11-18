import shutil
from pathlib import Path

from guardrails.task import create_task
from guardrails.trace import verify_trace

PACK = Path(__file__).resolve().parents[1] / "pack"


def _project(tmp_path: Path) -> Path:
    shutil.copytree(PACK / "templates", tmp_path / "templates")
    return tmp_path


def test_create_task_r1_writes_task_yaml(tmp_path):
    root = _project(tmp_path)
    result = create_task(
        root,
        task_id="order-cancel",
        title="订单取消",
        task_type="feature",
        risk="R1",
        files=["modules/order/src/cancel.ts"],
    )
    task_file = root / "specs" / "order-cancel" / "task.yaml"
    assert task_file.exists()
    text = task_file.read_text(encoding="utf-8")
    assert "id: order-cancel" in text
    assert "risk: R1" in text
    assert "  - modules/order/src/cancel.ts" in text
    assert (root / "specs" / "order-cancel" / "intent.md").exists()
    assert (root / "specs" / "order-cancel" / "spec.md").exists()
    assert (root / "specs" / "order-cancel" / "raw" / "manifest.json").exists()
    assert (root / "specs" / "order-cancel" / "trace.yaml").exists()
    assert not (root / "specs" / "order-cancel" / "plan.md").exists()
    assert "task.yaml" in result["created"]
    assert verify_trace(root, task="order-cancel")["ok"] is True


def test_create_task_r3_includes_plan(tmp_path):
    root = _project(tmp_path)
    create_task(root, "t3", "高风险", risk="R3")
    assert (root / "specs" / "t3" / "plan.md").exists()


def test_create_task_rejects_existing(tmp_path):
    root = _project(tmp_path)
    create_task(root, "t1", "T", risk="R0")
    try:
        create_task(root, "t1", "T", risk="R0")
    except Exception as exc:  # noqa: BLE001 - assertion below is the contract
        assert "already exists" in str(exc)
    else:
        raise AssertionError("expected create_task to reject an existing task")
