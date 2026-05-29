#!/usr/bin/env python3
"""
Simulate DNA assembly using pydna.

Usage:
    python src/tools/assembly.py --method gibson --parts insert.fa backbone.fa
    python src/tools/assembly.py --method restriction --parts insert.fa backbone.fa --enzymes EcoRI HindIII

Outputs JSON with simulated construct details.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from Bio import SeqIO
from pydna.dseqrecord import Dseqrecord
from pydna.assembly import Assembly

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
                return Dseqrecord(
                    str(records[0].seq), name=records[0].name or p.stem
                )
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
    from pydna.dseqrecord import Dseqrecord

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate DNA assembly")
    parser.add_argument("--method", required=True,
                        choices=["gibson", "restriction"],
                        help="Assembly method")
    parser.add_argument("--parts", nargs="+", required=True,
                        help="Input parts: file paths (.fa/.gb) or raw sequences")
    parser.add_argument("--enzymes", nargs="+", default=[],
                        help="Restriction enzymes (for --method restriction)")
    parser.add_argument("--overlap", type=int, default=20,
                        help="Minimum overlap for Gibson assembly (default 20bp)")
    args = parser.parse_args()

    if args.method == "gibson":
        result = simulate_gibson(args.parts, overlap_min=args.overlap)
    else:
        if not args.enzymes:
            print(json.dumps({"error": "--enzymes required for restriction method"}))
            sys.exit(1)
        result = simulate_restriction_ligation(args.parts, args.enzymes)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
