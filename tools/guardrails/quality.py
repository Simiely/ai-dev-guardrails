from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import Any

from .graph import EXCLUDE_DIRS, is_test_file
from .util import normalize_path

SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx"}
SKIP_PREFIXES = ("#", "//", "/*", "*", "import ", "from ", "export ", "require(")
SKIP_LINES = {")", "}", "]", "});", "};", "else:", "try:", "finally:"}


def _python_files(root: Path) -> list[Path]:
    result = []
    for path in root.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        result.append(path)
    return sorted(result)


def _complexity(func: ast.AST) -> int:
    score = 1
    stack = list(getattr(func, "body", []))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp, ast.ExceptHandler, ast.Assert)):
            score += 1
        elif isinstance(node, ast.BoolOp):
            score += max(0, len(node.values) - 1)
        elif isinstance(node, ast.comprehension):
            score += len(node.ifs)
        stack.extend(ast.iter_child_nodes(node))
    return score


def python_metrics(root: Path, files: list[str], max_complexity: int, max_length: int) -> dict[str, Any]:
    metrics = []
    violations = []
    for item in files:
        path = root / item
        if path.suffix != ".py" or not path.exists():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            violations.append({"file": item, "kind": "parse_error", "detail": "cannot parse Python"})
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            length = (getattr(node, "end_lineno", None) or node.lineno) - node.lineno + 1
            complexity = _complexity(node)
            entry = {
                "file": item,
                "function": node.name,
                "line": node.lineno,
                "length": length,
                "complexity": complexity,
            }
            metrics.append(entry)
            if length > max_length:
                violations.append(
                    {
                        "file": item,
                        "function": node.name,
                        "kind": "function_too_long",
                        "detail": f"{length} lines > {max_length}",
                    }
                )
            if complexity > max_complexity:
                violations.append(
                    {
                        "file": item,
                        "function": node.name,
                        "kind": "complexity_too_high",
                        "detail": f"complexity {complexity} > {max_complexity}",
                    }
                )
    return {"metrics": metrics, "violations": violations}


def _line_key(line: str) -> str | None:
    value = line.strip()
    if not value or value in SKIP_LINES:
        return None
    if value.startswith(SKIP_PREFIXES):
        return None
    return re.sub(r"\s+", " ", value)


def _source_files(root: Path) -> list[Path]:
    result = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if is_test_file(path, root):
            continue
        result.append(path)
    return sorted(result)


def duplicate_blocks(root: Path, changed: list[str], min_lines: int = 5) -> list[dict[str, Any]]:
    windows: dict[str, list[tuple[str, int]]] = {}
    for path in _source_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        keys = [(number, key) for number, line in enumerate(lines, 1) if (key := _line_key(line))]
        for index in range(0, len(keys) - min_lines + 1):
            chunk = keys[index : index + min_lines]
            digest = hashlib.sha256("\n".join(key for _, key in chunk).encode("utf-8")).hexdigest()[:16]
            windows.setdefault(digest, []).append(
                (normalize_path(str(path.relative_to(root))), chunk[0][0])
            )

    changed_set = set(changed)
    duplicates = []
    for digest, locations in windows.items():
        if len(locations) < 2:
            continue
        if changed_set and not any(file in changed_set for file, _ in locations):
            continue
        duplicates.append(
            {
                "hash": digest,
                "lines": min_lines,
                "locations": [
                    {"file": file, "line": line} for file, line in sorted(locations)[:5]
                ],
            }
        )
    return sorted(duplicates, key=lambda item: (item["locations"][0]["file"], item["locations"][0]["line"]))[:50]


def quality_report(
    root: Path,
    files: list[str],
    max_complexity: int = 10,
    max_function_length: int = 50,
    min_duplicate_lines: int = 5,
) -> dict[str, Any]:
    normalized = [normalize_path(item) for item in files]
    py = python_metrics(root, normalized, max_complexity, max_function_length)
    duplicates = duplicate_blocks(root, normalized, min_duplicate_lines)
    unsupported = []
    if any(item.endswith((".ts", ".tsx", ".js", ".jsx")) for item in normalized):
        unsupported.append("TypeScript/JavaScript complexity (not implemented)")
    return {
        "files": normalized,
        "metrics": py["metrics"],
        "violations": py["violations"],
        "duplicates": duplicates,
        "unsupported": unsupported,
        "summary": {
            "functions": len(py["metrics"]),
            "violations": len(py["violations"]),
            "duplicate_blocks": len(duplicates),
        },
    }
