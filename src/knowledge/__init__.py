"""Curated parts knowledge base with JSON Schema validation."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_KNOWLEDGE_DIR = Path(__file__).resolve().parent
_SCHEMA_DIR = _KNOWLEDGE_DIR / "schema"


def _validate_against_schema(data: object, schema_name: str) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema is required for knowledge validation") from exc

    schema_path = _SCHEMA_DIR / f"{schema_name}.json"
    schema = json.loads(schema_path.read_text())
    jsonschema.validate(instance=data, schema=schema)


@lru_cache(maxsize=8)
def _load(filename: str) -> dict:
    path = _KNOWLEDGE_DIR / filename
    data = json.loads(path.read_text())
    schema_name = filename.replace(".json", "")
    if (_SCHEMA_DIR / f"{schema_name}.json").exists():
        _validate_against_schema(data, schema_name)
    return data


def get_backbones() -> dict:
    return _load("backbones.json")


def get_promoters() -> dict:
    return _load("promoters.json")


def get_terminators() -> dict:
    return _load("terminators.json")


def get_selectable_markers() -> dict:
    return _load("selectable_markers.json")
