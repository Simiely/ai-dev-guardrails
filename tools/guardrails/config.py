from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from .util import GuardrailsError, read_text


def repo_schema(name: str) -> Path:
    # tools/guardrails/config.py -> repo root
    return Path(__file__).resolve().parents[2] / "schema" / name


def load_config(root: Path) -> dict[str, Any]:
    path = root / "guardrails.yaml"
    if not path.exists():
        raise GuardrailsError(f"missing {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise GuardrailsError(f"{path}: expected a mapping")
    schema_path = repo_schema("guardrails.schema.json")
    if schema_path.exists():
        schema = json.loads(read_text(schema_path))
        errors = sorted(
            Draft202012Validator(schema).iter_errors(raw),
            key=lambda error: list(error.path),
        )
        if errors:
            detail = "; ".join(
                f"{'/'.join(str(part) for part in error.path) or '$'}: {error.message}"
                for error in errors
            )
            raise GuardrailsError(f"{path}: {detail}")
    raw["_root"] = str(root.resolve())
    raw["_path"] = str(path.resolve())
    return raw
