from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .config import repo_schema
from .manual import Card, Chapter
from .util import read_text

CARD_SECTIONS = ("## 目标", "## 红线", "## 路由表", "## 状态与交接", "## 验证命令")
CONDITIONAL_RE = re.compile(r"(如果|如需|若是|假如|倘若)")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _add(bucket: list[dict[str, str]], code: str, path: Path, message: str) -> None:
    bucket.append({"code": code, "path": str(path), "message": message})


def _paragraphs(body: str) -> list[str]:
    paragraphs = []
    for part in re.split(r"\n\s*\n", body):
        normalized = re.sub(r"\s+", " ", part).strip()
        if len(re.sub(r"\s+", "", normalized)) >= 60:
            paragraphs.append(normalized)
    return paragraphs


def lint_manual(root: Path, config: dict[str, Any], card: Card, chapters: list[Chapter]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if card.lines > 80:
        _add(errors, "card.too_long", card.path, f"card has {card.lines} lines; max is 80")
    for section in CARD_SECTIONS:
        if section not in card.body:
            _add(errors, "card.missing_section", card.path, f"missing section {section!r}")

    schema_path = repo_schema("skill.schema.json")
    skill_schema = json.loads(read_text(schema_path)) if schema_path.exists() else None
    max_chapters = int(config.get("manual", {}).get("max_chapters", 6))

    if len(chapters) > max_chapters:
        _add(errors, "chapters.too_many", Path(config["_path"]), f"{len(chapters)} chapters; max is {max_chapters}")
    if len(chapters) < 2:
        _add(warnings, "chapters.too_few", Path(config["_path"]), "fewer than 2 chapters")

    names: set[str] = set()
    for chapter in chapters:
        if chapter.name in names:
            _add(errors, "chapter.duplicate_name", chapter.path, f"duplicate chapter name {chapter.name!r}")
        names.add(chapter.name)

        if skill_schema is not None:
            for error in sorted(
                Draft202012Validator(skill_schema).iter_errors(chapter.meta),
                key=lambda item: list(item.path),
            ):
                where = ".".join(str(part) for part in error.path) or "$"
                _add(errors, "chapter.schema", chapter.path, f"{where}: {error.message}")

        if chapter.name != chapter.path.parent.name:
            _add(
                warnings,
                "chapter.dir_name_mismatch",
                chapter.path,
                f"directory {chapter.path.parent.name!r} != name {chapter.name!r}",
            )

        description = chapter.description
        if "用于" not in description and "当" not in description:
            _add(errors, "chapter.description_when", chapter.path, "description must say when to use")
        if "不要" not in description and "不在" not in description:
            _add(errors, "chapter.description_when_not", chapter.path, "description must say when NOT to use")

        if not chapter.when_to_use:
            _add(errors, "chapter.when_to_use", chapter.path, "when_to_use is empty")
        if not chapter.when_not_to_use:
            _add(errors, "chapter.when_not_to_use", chapter.path, "when_not_to_use is empty")
        if chapter.tokens > chapter.budget:
            _add(
                errors,
                "chapter.over_budget",
                chapter.path,
                f"estimated {chapter.tokens} tokens > budget {chapter.budget}",
            )

        for line_no, line in enumerate(chapter.body.splitlines(), 1):
            if CONDITIONAL_RE.search(line):
                _add(
                    errors,
                    "chapter.conditional",
                    chapter.path,
                    f"line {line_no}: conditional phrasing is less reliably followed: {line.strip()}",
                )
            for target in LINK_RE.findall(line):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                resolved = (chapter.path.parent / target.split("#", 1)[0]).resolve()
                if not resolved.exists():
                    _add(errors, "chapter.broken_link", chapter.path, f"line {line_no}: {target}")

    for chapter in chapters:
        for related in chapter.related:
            if related not in names:
                _add(errors, "chapter.unknown_related", chapter.path, f"related chapter {related!r} does not exist")

    seen: dict[str, str] = {}
    for chapter in chapters:
        for paragraph in _paragraphs(chapter.body):
            key = re.sub(r"\s+", "", paragraph)
            if key in seen and seen[key] != chapter.name:
                _add(
                    errors,
                    "chapter.duplicate_paragraph",
                    chapter.path,
                    f"duplicates content from {seen[key]!r}: {paragraph[:60]}...",
                )
            else:
                seen[key] = chapter.name

    for name in names:
        if name not in card.body:
            _add(
                warnings,
                "card.missing_route",
                card.path,
                f"chapter {name!r} is not mentioned in the routing card",
            )

    return {
        "errors": errors,
        "warnings": warnings,
        "chapters": len(chapters),
        "card_lines": card.lines,
    }
