"""Cloning strategy — describes how to assemble parts into a construct."""
from __future__ import annotations
from dataclasses import dataclass

from .part import BiologicalPart
from .plasmid import CloningMethod


@dataclass(frozen=True)
class Primer:
    """A PCR primer."""
    name: str
    sequence: str          # Full primer sequence (binding region + overhang)
    binding_region: str    # The ~20bp that anneals to template
    overhang: str = ""     # Extra 5' sequence for Gibson/GoldenGate
    tm_celsius: float = 0.0

    @property
    def length(self) -> int:
        return len(self.sequence)


@dataclass(frozen=True)
class CloningStrategy:
    """
    Describes a complete cloning plan: backbone + insert(s) + primers + method.
    Immutable — produce a new one if the strategy changes.
    """
    method: CloningMethod
    backbone: BiologicalPart
    inserts: tuple[BiologicalPart, ...]
    forward_primer: Primer
    reverse_primer: Primer
    expected_size_bp: int
    notes: str = ""

    @property
    def all_parts(self) -> tuple[BiologicalPart, ...]:
        return (self.backbone,) + self.inserts
