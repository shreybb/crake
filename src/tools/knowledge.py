"""Load and query the knowledge base JSON files."""
from __future__ import annotations
import json
from pathlib import Path

_KB_DIR = Path(__file__).parent.parent / "knowledge"


def _load(filename: str) -> dict:
    return json.loads((_KB_DIR / filename).read_text())


def get_backbones() -> dict:
    return _load("backbones.json")


def get_promoters() -> dict:
    return _load("promoters.json")


def get_terminators() -> dict:
    return _load("terminators.json")


def get_selectable_markers() -> dict:
    return _load("selectable_markers.json")


def suggest_backbone(host: str, purpose: str = "") -> list[dict]:
    """Return a list of suitable backbones for the given host."""
    data = get_backbones()
    results = []
    if host == "e_coli":
        for name, info in data.get("e_coli", {}).items():
            results.append({"name": name, **info})
    elif host in ("agrobacterium", "plant_nuclear"):
        for name, info in data.get("plant_binary", {}).items():
            results.append({"name": name, **info})
    return results


def suggest_promoter(host: str) -> list[dict]:
    """Return suitable promoters for the given host."""
    data = get_promoters()
    if host == "e_coli":
        return [{"name": k, **v} for k, v in data.get("e_coli", {}).items()]
    elif host in ("agrobacterium", "plant_nuclear"):
        return [{"name": k, **v} for k, v in data.get("plant", {}).items()]
    return []


def suggest_terminator(host: str) -> list[dict]:
    data = get_terminators()
    if host == "e_coli":
        return [{"name": k, **v} for k, v in data.get("e_coli", {}).items()]
    elif host in ("agrobacterium", "plant_nuclear"):
        return [{"name": k, **v} for k, v in data.get("plant", {}).items()]
    return []


def suggest_selectable_marker(host: str) -> list[dict]:
    data = get_selectable_markers()
    if host == "e_coli":
        return [{"name": k, **v} for k, v in data.get("e_coli", {}).items()]
    elif host in ("agrobacterium", "plant_nuclear"):
        return [{"name": k, **v} for k, v in data.get("plant", {}).items()]
    return []
