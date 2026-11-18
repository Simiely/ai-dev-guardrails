from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .util import GuardrailsError, estimate_tokens, read_text, split_frontmatter


@dataclass
class Chapter:
    name: str
    path: Path
    meta: dict[str, Any]
    body: str
    tokens: int

    @property
    def description(self) -> str:
        value = self.meta.get("description", "")
        return " ".join(str(value).split())

    @property
    def when_to_use(self) -> list[str]:
        value = self.meta.get("when_to_use", [])
        return [str(item) for item in value] if isinstance(value, list) else []

    @property
    def when_not_to_use(self) -> list[str]:
        value = self.meta.get("when_not_to_use", [])
        return [str(item) for item in value] if isinstance(value, list) else []

    @property
    def globs(self) -> list[str]:
        value = self.meta.get("globs", [])
        return [str(item) for item in value] if isinstance(value, list) else []

    @property
    def related(self) -> list[str]:
        value = self.meta.get("related", [])
        return [str(item) for item in value] if isinstance(value, list) else []

    @property
    def budget(self) -> int:
        value = self.meta.get("token_budget")
        return int(value) if isinstance(value, int) else 1200


@dataclass
class Card:
    path: Path
    meta: dict[str, Any]
    body: str
    lines: int


def load_card(root: Path, config: dict[str, Any]) -> Card:
    value = config.get("manual", {}).get("card", "manual/00-card.md")
    path = root / value
    if not path.exists():
        raise GuardrailsError(f"missing manual card: {path}")
    meta, body = split_frontmatter(read_text(path))
    return Card(path=path, meta=meta, body=body, lines=len(read_text(path).splitlines()))


def load_chapters(root: Path, config: dict[str, Any]) -> list[Chapter]:
    value = config.get("manual", {}).get("chapters", "manual/chapters")
    directory = root / value
    if not directory.exists():
        raise GuardrailsError(f"missing chapter directory: {directory}")
    chapters: list[Chapter] = []
    for skill_path in sorted(directory.glob("*/SKILL.md")):
        meta, body = split_frontmatter(read_text(skill_path))
        name = str(meta.get("name") or skill_path.parent.name)
        chapters.append(
            Chapter(
                name=name,
                path=skill_path,
                meta=meta,
                body=body,
                tokens=estimate_tokens(body),
            )
        )
    return chapters


def chapter_map(chapters: list[Chapter]) -> dict[str, Chapter]:
    return {chapter.name: chapter for chapter in chapters}


def selected_token_estimate(chapters: list[Chapter], selected: list[str]) -> int:
    by_name = chapter_map(chapters)
    return sum(by_name[name].budget for name in selected if name in by_name)


def load_manual(root: Path, config: dict[str, Any]) -> tuple[Card, list[Chapter]]:
    return load_card(root, config), load_chapters(root, config)
