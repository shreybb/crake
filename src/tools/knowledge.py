"""Load and query the knowledge base JSON files."""

from __future__ import annotations

from src.knowledge import (
    get_backbones,
    get_promoters,
    get_selectable_markers,
    get_terminators,
)

_PLASTID_NOTE = {
    "name": "plant_plastid",
    "note": (
        "Plastid transformation is not yet in the Crake knowledge base. "
        "Common vectors: pLD-ctv, pHK20. Promoter: Prrn (rRNA operon). "
        "Marker: aadA (spectinomycin/streptomycin resistance). "
        "Please consult the literature or provide your own parts."
    ),
    "supported": False,
}


def suggest_backbone(host: str, purpose: str = "") -> list[dict]:
    """Return a list of suitable backbones for the given host."""
    data = get_backbones()
    if host == "e_coli":
        return [{"name": k, **v} for k, v in data.get("e_coli", {}).items()]
    elif host == "yeast":
        return [{"name": k, **v} for k, v in data.get("yeast", {}).items()]
    elif host in ("agrobacterium", "plant_nuclear"):
        return [{"name": k, **v} for k, v in data.get("plant_binary", {}).items()]
    elif host == "plant_plastid":
        return [_PLASTID_NOTE]
    return []


def suggest_promoter(host: str) -> list[dict]:
    """Return suitable promoters for the given host."""
    data = get_promoters()
    if host == "e_coli":
        return [{"name": k, **v} for k, v in data.get("e_coli", {}).items()]
    elif host == "yeast":
        return [{"name": k, **v} for k, v in data.get("yeast", {}).items()]
    elif host in ("agrobacterium", "plant_nuclear"):
        return [{"name": k, **v} for k, v in data.get("plant", {}).items()]
    elif host == "plant_plastid":
        return [_PLASTID_NOTE]
    return []


def suggest_terminator(host: str) -> list[dict]:
    data = get_terminators()
    if host == "e_coli":
        return [{"name": k, **v} for k, v in data.get("e_coli", {}).items()]
    elif host == "yeast":
        return [{"name": k, **v} for k, v in data.get("yeast", {}).items()]
    elif host in ("agrobacterium", "plant_nuclear"):
        return [{"name": k, **v} for k, v in data.get("plant", {}).items()]
    elif host == "plant_plastid":
        return [_PLASTID_NOTE]
    return []


def suggest_selectable_marker(host: str) -> list[dict]:
    data = get_selectable_markers()
    if host == "e_coli":
        return [{"name": k, **v} for k, v in data.get("e_coli", {}).items()]
    elif host == "yeast":
        return [{"name": k, **v} for k, v in data.get("yeast", {}).items()]
    elif host in ("agrobacterium", "plant_nuclear"):
        return [{"name": k, **v} for k, v in data.get("plant", {}).items()]
    elif host == "plant_plastid":
        return [_PLASTID_NOTE]
    return []
