from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from .util import normalize_path

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".guardrails",
    "coverage",
}
PY_SUFFIXES = {".py"}
TS_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
TS_IMPORT_RE = re.compile(
    r"""(?:import|export)\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]"""
    r"""|require\(\s*['"]([^'"]+)['"]\s*\)"""
)


def _iter_files(root: Path, suffixes: set[str]) -> list[Path]:
    result: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        result.append(path)
    return sorted(result)


def _module_name(root: Path, path: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _add_module_candidates(name: str, module_map: dict[str, Path], result: set[Path]) -> None:
    if not name:
        return
    parts = name.split(".")
    for index in range(len(parts), 0, -1):
        candidate = ".".join(parts[:index])
        if candidate in module_map:
            result.add(module_map[candidate])
            return


def _python_imports(path: Path, root: Path, module_map: dict[str, Path]) -> set[Path]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return set()

    current_module = _module_name(root, path)
    current_pkg = current_module if path.name == "__init__.py" else current_module.rsplit(".", 1)[0]
    result: set[Path] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _add_module_candidates(alias.name, module_map, result)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                package_parts = current_pkg.split(".") if current_pkg else []
                up = node.level - 1
                if up > len(package_parts):
                    continue
                base_parts = package_parts[: len(package_parts) - up] if up else package_parts
                base = ".".join(base_parts + ([base] if base else []))
            _add_module_candidates(base, module_map, result)
            for alias in node.names:
                if alias.name == "*":
                    continue
                child = f"{base}.{alias.name}" if base else alias.name
                _add_module_candidates(child, module_map, result)
    return result


def _ts_candidates(base: Path) -> list[Path]:
    return [
        base,
        base.with_suffix(".ts"),
        base.with_suffix(".tsx"),
        base.with_suffix(".js"),
        base.with_suffix(".jsx"),
        base.with_suffix(".mjs"),
        base.with_suffix(".cjs"),
        base / "index.ts",
        base / "index.tsx",
        base / "index.js",
        base / "index.jsx",
    ]


def _ts_imports(path: Path, all_files: set[Path]) -> set[Path]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()
    specs = [first or second for first, second in TS_IMPORT_RE.findall(text)]
    result: set[Path] = set()
    for spec in specs:
        if not spec.startswith("."):
            continue
        base = (path.parent / spec).resolve()
        for candidate in _ts_candidates(base):
            if candidate in all_files:
                result.add(candidate)
                break
    return result


def is_test_file(path: Path, root: Path | None = None) -> bool:
    name = path.name
    parts = path.relative_to(root).parts if root is not None else path.parts
    if path.suffix == ".py":
        return name.startswith("test_") or name.endswith("_test.py")
    if path.suffix in TS_SUFFIXES:
        return (
            ".test." in name
            or ".spec." in name
            or "tests" in parts
            or "__tests__" in parts
        )
    return False


def _transitive(graph: dict[Path, set[Path]], start: Path) -> set[Path]:
    seen: set[Path] = set()
    stack = [start]
    while stack:
        node = stack.pop()
        for dep in graph.get(node, set()):
            if dep not in seen:
                seen.add(dep)
                stack.append(dep)
    return seen


def build_graph(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    py_files = _iter_files(root, PY_SUFFIXES)
    ts_files = _iter_files(root, TS_SUFFIXES)
    all_files = set(py_files + ts_files)

    module_map = {_module_name(root, path): path for path in py_files if path.name != "__init__.py"}
    for path in py_files:
        if path.name == "__init__.py":
            module_map[_module_name(root, path)] = path

    graph: dict[Path, set[Path]] = {}
    for path in py_files:
        graph[path] = _python_imports(path, root, module_map)
    ts_set = set(ts_files)
    for path in ts_files:
        graph[path] = _ts_imports(path, ts_set)

    tests = [path for path in all_files if is_test_file(path, root)]
    return {"graph": graph, "tests": tests, "files": all_files}


def affected_tests(
    root: Path,
    config: dict[str, Any],
    changed_files: list[str],
) -> dict[str, Any]:
    changed = [normalize_path(item) for item in changed_files if item]
    graph_data = build_graph(root, config)
    graph = graph_data["graph"]
    tests = graph_data["tests"]
    all_files = graph_data["files"]

    changed_paths = {(root / item).resolve() for item in changed}
    reasons: dict[str, list[str]] = {}
    affected: set[Path] = set()

    for test in tests:
        deps = _transitive(graph, test)
        deps.add(test)
        hits = sorted(normalize_path(str(path.relative_to(root))) for path in deps & changed_paths)
        if hits:
            affected.add(test)
            reasons[normalize_path(str(test.relative_to(root)))] = [f"depends on {hit}" for hit in hits]

    modules = config.get("modules", [])
    for changed_path in changed_paths:
        for module in modules:
            module_path = (root / str(module.get("path", ""))).resolve()
            try:
                changed_path.relative_to(module_path)
            except ValueError:
                continue
            module_name = str(module.get("name", ""))
            for test in tests:
                try:
                    test.relative_to(module_path)
                except ValueError:
                    continue
                affected.add(test)
                reasons.setdefault(normalize_path(str(test.relative_to(root))), []).append(
                    f"module ownership: {module_name}"
                )

    contract_paths = {
        normalize_path(str(item.get("path", ""))) for item in config.get("contracts", [])
    }
    contract_hit = any(
        item in contract_paths or item.startswith(("openapi/", "migrations/", "auth/"))
        for item in changed
    )
    fallback = "none"
    if contract_hit:
        affected = set(tests)
        fallback = "contract"
        for test in tests:
            reasons.setdefault(normalize_path(str(test.relative_to(root))), []).append(
                "contract change: run all tests"
            )

    if not affected and tests:
        fallback = "none"

    return {
        "changed": changed,
        "affected_tests": sorted(normalize_path(str(path.relative_to(root))) for path in affected),
        "reasons": dict(sorted(reasons.items())),
        "stats": {
            "files": len(all_files),
            "tests": len(tests),
            "edges": sum(len(deps) for deps in graph.values()),
        },
        "fallback": fallback,
    }
