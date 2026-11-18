from __future__ import annotations

from pathlib import Path
from typing import Any

from .graph import affected_tests
from .risk import LOCKFILES, classify
from .route import load_task
from .util import normalize_path


def build_card(
    root: Path,
    config: dict[str, Any],
    task_path: Path,
    files: list[str] | None = None,
) -> dict[str, Any]:
    task = load_task(task_path)
    selected = [normalize_path(item) for item in (files or task.files)]
    risk = classify(selected, config)
    level = task.risk or risk["level"]

    contracts = [
        str(item.get("id"))
        for item in config.get("contracts", [])
        if normalize_path(str(item.get("path", ""))) in selected
    ]
    dependencies = [
        item for item in selected if item.rsplit("/", 1)[-1] in LOCKFILES
    ]
    affected = affected_tests(root, config, selected) if selected else {"affected_tests": []}

    lines = [
        f"# 后果卡：{task.id}",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 类型 | {task.type or 'unknown'} |",
        f"| 风险 | {level} |",
        f"| 目标 | {task.goal or '-'} |",
        f"| 触及模块 | {', '.join(risk['modules']) or '无'} |",
        f"| 契约变更 | {', '.join(contracts) or '无'} |",
        f"| 新增依赖 | {', '.join(dependencies) or '无'} |",
        f"| 受影响测试 | {len(affected['affected_tests'])} |",
        "| 回滚 | `git revert <sha>` + migration down（如适用） |",
        "| 批准 SHA | `<pending>` |",
        "",
        "## 风险理由",
        "",
    ]
    for reason in risk["reasons"]:
        lines.append(f"- {reason}")
    if not risk["reasons"]:
        lines.append("- 无")
    lines += ["", "## 受影响测试", ""]
    for test in affected["affected_tests"]:
        lines.append(f"- `{test}`")
    if not affected["affected_tests"]:
        lines.append("- 无（未指定文件或未找到测试）")
    lines += ["", "## 回滚", "", "- revert commit", "- 数据迁移 down（如适用）", "- 功能开关关闭（如适用）", ""]

    return {
        "task": task.id,
        "type": task.type,
        "risk": level,
        "modules": risk["modules"],
        "contracts": contracts,
        "dependencies": dependencies,
        "affected_tests": affected["affected_tests"],
        "markdown": "\n".join(lines),
    }
