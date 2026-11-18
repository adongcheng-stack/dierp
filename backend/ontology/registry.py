"""Ontology registry: runtime access to the enum single source of truth.

The business services use these helpers so that a value accepted by the API can
never silently drift from ontology/src/mappings.json (which is also mirrored to
SHACL sh:in and generated TypeScript types).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MAPPINGS_FILE = ROOT / "ontology" / "src" / "mappings.json"
MODEL_FILE = ROOT / "ontology" / "model" / "planning.yaml"


@lru_cache(maxsize=1)
def mappings() -> dict[str, Any]:
    return json.loads(MAPPINGS_FILE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def enumerations() -> dict[str, tuple[str, ...]]:
    return {
        name: tuple(values)
        for name, values in mappings().get("enumerations", {}).items()
    }


def ontology_namespace() -> str:
    return mappings().get("namespace", "")


def is_valid(enum_name: str, value: Any) -> bool:
    values = enumerations().get(enum_name)
    if values is None:
        raise KeyError(f"未知本体枚举: {enum_name}")
    if value is None:
        return True
    raw = value.value if hasattr(value, "value") else str(value)
    return raw in values


def validate_enum(enum_name: str, value: Any, *, field: str | None = None) -> str:
    """Validate and return the plain string value of an enum member."""
    if value is None:
        return value
    raw = value.value if hasattr(value, "value") else str(value)
    if not is_valid(enum_name, raw):
        allowed = ", ".join(enumerations()[enum_name])
        raise ValueError(
            f"{field or enum_name}={raw!r} 不在本体枚举 {enum_name} 中；允许值: {allowed}"
        )
    return raw


@lru_cache(maxsize=1)
def model_entities() -> dict[str, Any]:
    """Operational model metadata (entities/fields) used by admin/debug APIs."""
    try:
        import yaml

        return yaml.safe_load(MODEL_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
