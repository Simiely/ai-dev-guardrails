from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml


class GuardrailsError(Exception):
    """User-facing error."""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(read_text(path))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise GuardrailsError(f"{path}: expected a YAML mapping")
    return data


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False).rstrip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a Markdown file into YAML frontmatter and body."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    fm_text = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    data = yaml.safe_load(fm_text) or {}
    if not isinstance(data, dict):
        raise GuardrailsError("frontmatter must be a mapping")
    return data, body


def render_frontmatter(data: dict[str, Any]) -> str:
    return "---\n" + dump_yaml(data) + "\n---\n"


def estimate_tokens(text: str) -> int:
    """Cheap, deterministic token estimate for mixed Chinese/English text."""
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    words = len(re.findall(r"[A-Za-z0-9_]+", text))
    return max(1, int(cjk / 1.5 + words * 1.3))


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    pattern = pattern.replace("\\", "/").strip()
    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern[i : i + 2] == "**":
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append(".")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def matches_any(path: str, patterns: list[str]) -> bool:
    p = normalize_path(path)
    for pattern in patterns:
        if glob_to_regex(pattern).match(p):
            return True
    return False


def module_for_path(path: str, modules: list[dict[str, Any]]) -> str | None:
    p = normalize_path(path)
    best: str | None = None
    best_len = -1
    for module in modules:
        mp = normalize_path(str(module.get("path", ""))).rstrip("/")
        if mp and (p == mp or p.startswith(mp + "/")) and len(mp) > best_len:
            best = str(module.get("name"))
            best_len = len(mp)
    return best


def is_docs_path(path: str) -> bool:
    p = normalize_path(path)
    return p.endswith(".md") or p.startswith("docs/") or p.startswith("README") or p.startswith("CHANGELOG")


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def resolve_under(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    root_resolved = root.resolve()
    try:
        path.relative_to(root_resolved)
    except ValueError as exc:
        raise GuardrailsError(f"path escapes project root: {value}") from exc
    return path
