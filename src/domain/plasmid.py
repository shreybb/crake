"""Plasmid — a circular construct composed of biological parts."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

from .part import BiologicalPart, Host

CloningMethod = Literal["gibson", "golden_gate", "restriction_ligation", "ligation_independent"]
Topology = Literal["circular", "linear"]


@dataclass(frozen=True)
class Feature:
    """Annotated region on a sequence."""
    name: str
    feature_type: str      # e.g. "CDS", "promoter", "terminator", "rep_origin"
    start: int             # 0-based, inclusive
    end: int               # 0-based, exclusive
    strand: Literal[1, -1] = 1
    qualifiers: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Plasmid:
    """Immutable plasmid construct."""
    name: str
    sequence: str
    topology: Topology = "circular"
    host: Host = "e_coli"
    features: tuple[Feature, ...] = ()
    parts: tuple[BiologicalPart, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        if not self.sequence:
            raise ValueError(f"Plasmid '{self.name}' has empty sequence")
        object.__setattr__(self, "sequence", self.sequence.upper())

    @property
    def length(self) -> int:
        return len(self.sequence)

    def with_feature(self, feature: Feature) -> "Plasmid":
        """Return new plasmid with an additional feature."""
        return Plasmid(
            name=self.name,
            sequence=self.sequence,
            topology=self.topology,
            host=self.host,
            features=self.features + (feature,),
            parts=self.parts,
            description=self.description,
        )
