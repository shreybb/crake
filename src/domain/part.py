"""Biological part — a named, typed DNA sequence fragment."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

PartType = Literal[
    "backbone", "insert", "promoter", "terminator",
    "selectable_marker", "reporter", "regulatory", "other"
]

Host = Literal["e_coli", "yeast", "agrobacterium", "plant_nuclear", "plant_plastid"]


@dataclass(frozen=True)
class BiologicalPart:
    """Immutable representation of a DNA part."""
    name: str
    sequence: str          # Raw DNA sequence, uppercase ATCG
    part_type: PartType
    compatible_hosts: tuple[Host, ...]
    description: str = ""
    source: str = ""       # e.g. "Addgene #12345", "GenBank AY093066"

    def __post_init__(self) -> None:
        if not self.sequence:
            raise ValueError(f"Part '{self.name}' has empty sequence")
        invalid = set(self.sequence.upper()) - set("ATCGN")
        if invalid:
            raise ValueError(
                f"Part '{self.name}' contains invalid bases: {invalid}"
            )
        # Normalize to uppercase (frozen dataclass requires object.__setattr__)
        object.__setattr__(self, "sequence", self.sequence.upper())

    @property
    def length(self) -> int:
        return len(self.sequence)
