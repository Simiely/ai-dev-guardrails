from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from .util import GuardrailsError


def source_root() -> Path:
    """Repository root for editable/source installs."""
    return Path(__file__).resolve().parents[2]


def asset_path(*parts: str) -> Path:
    """Resolve a packaged asset in source or installed layouts.

    Source/editable installs keep ``pack/`` and ``schema/`` at the repo root.
    Wheels copy them to ``guardrails/_assets/`` via ``setup.py``.
    """
    candidate = source_root().joinpath(*parts)
    if candidate.exists():
        return candidate

    try:
        resource = files("guardrails").joinpath("_assets", *parts)
    except (ModuleNotFoundError, AttributeError) as exc:
        raise GuardrailsError(f"missing packaged asset: {'/'.join(parts)}") from exc

    if isinstance(resource, Path):
        path = Path(resource)
        if path.exists():
            return path

    raise GuardrailsError(
        f"missing packaged asset: {'/'.join(parts)}; "
        "reinstall the package or pass an explicit --source"
    )
