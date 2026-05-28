"""Enumerate part names from the curated knowledge-base JSON files."""
from __future__ import annotations

import json
from pathlib import Path

_KB_DIR = Path(__file__).parent.parent / "knowledge"


def list_part_names() -> dict[str, list[str]]:
    """Return all part names grouped by category (backbones, promoters, …)."""
    files = {
        "backbones": _KB_DIR / "backbones.json",
        "promoters": _KB_DIR / "promoters.json",
        "terminators": _KB_DIR / "terminators.json",
        "markers": _KB_DIR / "selectable_markers.json",
    }
    parts: dict[str, list[str]] = {key: [] for key in files}
    for key, path in files.items():
        try:
            data = json.loads(path.read_text())
            names: list[str] = []
            for host_entries in data.values():
                if isinstance(host_entries, dict):
                    names.extend(host_entries.keys())
            parts[key] = sorted(names)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    return parts
