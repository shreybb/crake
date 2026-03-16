#!/usr/bin/env python3
"""
Annotate features in a DNA sequence using BioPython restriction analysis.

Usage:
    python src/tools/annotation.py --sequence ATCG... [--output json]
    python src/tools/annotation.py --file sequence.gb [--output json]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Restriction import RestrictionBatch, Analysis, CommOnly


def find_restriction_sites(sequence: str, common_only: bool = True) -> list[dict]:
    """Return restriction sites found in the sequence."""
    seq = Seq(sequence)
    batch = CommOnly  # common restriction enzymes
    analysis = Analysis(batch, seq, linear=False)
    results = analysis.full()

    sites = []
    for enzyme, positions in results.items():
        if positions:
            sites.append({
                "enzyme": str(enzyme),
                "positions": positions,
                "cut_count": len(positions),
            })
    return sorted(sites, key=lambda x: x["enzyme"])


def annotate_from_genbank(filepath: str) -> dict:
    """Read a GenBank file and return features as JSON-serializable dicts."""
    record = SeqIO.read(filepath, "genbank")
    features = []
    for feat in record.features:
        features.append({
            "type": feat.type,
            "location": str(feat.location),
            "start": int(feat.location.start),
            "end": int(feat.location.end),
            "strand": feat.location.strand,
            "qualifiers": {k: v[0] if len(v) == 1 else v
                           for k, v in feat.qualifiers.items()},
        })
    return {
        "name": record.name,
        "description": record.description,
        "length": len(record.seq),
        "topology": record.annotations.get("topology", "unknown"),
        "features": features,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Annotate DNA sequence features")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sequence", help="Raw DNA sequence string")
    group.add_argument("--file", help="Path to GenBank (.gb) file")
    parser.add_argument("--restriction-sites", action="store_true",
                        help="Find common restriction enzyme sites")
    args = parser.parse_args()

    output: dict = {}

    if args.file:
        output = annotate_from_genbank(args.file)
    elif args.sequence:
        output["sequence_length"] = len(args.sequence)
        output["gc_content"] = round(
            (args.sequence.upper().count("G") + args.sequence.upper().count("C"))
            / len(args.sequence) * 100, 2
        )

    if args.restriction_sites or args.sequence:
        seq = args.sequence or ""
        if not seq and args.file:
            record = SeqIO.read(args.file, "genbank")
            seq = str(record.seq)
        output["restriction_sites"] = find_restriction_sites(seq)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
