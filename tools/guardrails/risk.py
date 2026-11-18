from __future__ import annotations

from typing import Any

from .util import is_docs_path, matches_any, module_for_path, normalize_path

LOCKFILES = {"package.json", "pyproject.toml", "pom.xml", "build.gradle", "go.mod", "Cargo.toml"}


def classify(files: list[str], config: dict[str, Any]) -> dict[str, Any]:
    files = [normalize_path(f) for f in files if f]
    if not files:
        return {"level": "R1", "reasons": ["no files provided; default R1"], "modules": []}

    risk_cfg = config.get("risk", {})
    modules_cfg = config.get("modules", [])
    contract_paths = [normalize_path(str(item.get("path", ""))) for item in config.get("contracts", [])]

    modules = sorted(
        {
            module
            for file in files
            if (module := module_for_path(file, modules_cfg)) is not None
        }
    )

    reasons: list[str] = []
    level = "R1"

    r3_patterns = list(risk_cfg.get("R3", []))
    r3_hits = [file for file in files if matches_any(file, r3_patterns)]
    contract_hits = [file for file in files if file in contract_paths]
    lock_hits = [file for file in files if file.rsplit("/", 1)[-1] in LOCKFILES]
    core_hits = [file for file in files if file in {"guardrails.yaml", "ARCHITECTURE.md"}]

    if r3_hits or contract_hits or lock_hits or core_hits:
        level = "R3"
        for file in sorted(set(r3_hits + contract_hits + lock_hits + core_hits)):
            reasons.append(f"R3 path: {file}")
    elif len(modules) > 1:
        level = "R2"
        reasons.append(f"touches {len(modules)} modules: {', '.join(modules)}")
    elif all(is_docs_path(file) for file in files):
        level = "R0"
        reasons.append("docs-only change")
    elif modules:
        level = "R1"
        reasons.append(f"single module: {modules[0]}")
    else:
        level = "R1"
        reasons.append("no registered module matched; default R1")

    return {"level": level, "reasons": reasons, "modules": modules}
