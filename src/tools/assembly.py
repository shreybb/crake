#!/usr/bin/env python3
"""
Simulate DNA assembly using pydna.

CLI: ``crake cmd "/assemble gibson backbone.fa"`` (after loading the insert sequence).
"""

from __future__ import annotations

from pathlib import Path

from Bio import SeqIO
from pydna.assembly import Assembly
from pydna.dseqrecord import Dseqrecord

_DNA_CHARS = frozenset("ACGTUNRYMKSWHBVD")
_SEQUENCE_FILE_SUFFIXES = {".fa", ".fasta", ".gb", ".genbank", ".dna"}


def _is_raw_dna(text: str) -> bool:
    """True when *text* looks like a nucleotide string, not a file path."""
    stripped = text.strip()
    if not stripped:
        return False
    if "/" in stripped or "\\" in stripped:
        return False
    upper = stripped.upper()
    return bool(upper) and set(upper) <= _DNA_CHARS


def _load_sequence(path_or_seq: str) -> Dseqrecord:
    """Load a sequence from a file path or raw string."""
    stripped = path_or_seq.strip()
    suffix = Path(stripped).suffix.lower()
    if suffix in _SEQUENCE_FILE_SUFFIXES or "/" in stripped or "\\" in stripped:
        try:
            p = Path(stripped)
            if p.is_file():
                fmt = "fasta" if suffix in (".fa", ".fasta") else "genbank"
                records = list(SeqIO.parse(str(p), fmt))
                if not records:
                    raise ValueError(f"No sequences found in {p}")
                return Dseqrecord(str(records[0].seq), name=records[0].name or p.stem)
        except OSError:
            pass
    if _is_raw_dna(stripped):
        return Dseqrecord(stripped.upper(), name="sequence")
    try:
        p = Path(stripped)
        if p.is_file():
            fmt = "fasta" if p.suffix.lower() in (".fa", ".fasta") else "genbank"
            records = list(SeqIO.parse(str(p), fmt))
            if not records:
                raise ValueError(f"No sequences found in {p}")
            return Dseqrecord(str(records[0].seq), name=records[0].name or p.stem)
    except OSError:
        pass
    return Dseqrecord(stripped.upper(), name="sequence")


def simulate_gibson(fragments: list[str], overlap_min: int = 20) -> dict:
    """Simulate Gibson Assembly."""
    parts = [_load_sequence(f) for f in fragments]
    assembly = Assembly(parts, limit=overlap_min)
    assembled = assembly.assemble_circular()

    if not assembled:
        # Try linear
        assembled = assembly.assemble_linear()
        if not assembled:
            return {
                "success": False,
                "error": f"No assembly products found. Check overlaps (min overlap: {overlap_min} bp).",
                "parts": [{"name": p.name, "length": len(p)} for p in parts],
            }
        topology = "linear"
    else:
        topology = "circular"

    top = assembled[0]
    return {
        "success": True,
        "method": "gibson",
        "topology": topology,
        "product_length_bp": len(top),
        "product_sequence": str(top.seq),
        "num_alternatives": len(assembled),
        "input_parts": [{"name": p.name, "length": len(p)} for p in parts],
    }


def simulate_restriction_ligation(
    fragments: list[str],
    enzymes: list[str],
) -> dict:
    """Simulate restriction enzyme digest + ligation."""
    from Bio.Restriction import RestrictionBatch

    batch = RestrictionBatch(enzymes)
    digested_parts = []

    for frag_path in fragments:
        part = _load_sequence(frag_path)
        cuts = part.cut(batch)
        digested_parts.extend(cuts)

    if not digested_parts:
        return {"success": False, "error": "No fragments produced by digestion"}

    assembly = Assembly(digested_parts, limit=4)  # sticky ends are ~4bp
    assembled = assembly.assemble_circular()

    if not assembled:
        return {
            "success": False,
            "error": "Ligation failed — incompatible sticky ends or wrong enzyme pair",
            "digested_fragments": [{"length": len(f)} for f in digested_parts],
        }

    top = assembled[0]
    return {
        "success": True,
        "method": "restriction_ligation",
        "enzymes": enzymes,
        "product_length_bp": len(top),
        "product_sequence": str(top.seq),
        "topology": "circular",
        "digested_fragment_count": len(digested_parts),
    }
