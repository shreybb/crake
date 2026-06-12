#!/usr/bin/env python3
"""
Annotate features in a DNA sequence using BioPython restriction analysis.

CLI: ``crake cmd "/annotate"`` (after loading a sequence).
"""

from __future__ import annotations

from Bio import SeqIO
from Bio.Restriction import Analysis, CommOnly
from Bio.Seq import Seq


def find_restriction_sites(
    sequence: str,
    common_only: bool = True,
    linear: bool = False,
) -> list[dict]:
    """Return restriction sites found in the sequence.

    Args:
        sequence: DNA sequence to scan.
        common_only: When True (default), only search CommOnly enzymes.
        linear: When True, treat the sequence as linear (e.g. a PCR product).
            When False (default), treat as circular (standard plasmid).
    """
    seq = Seq(sequence)
    batch = CommOnly  # common restriction enzymes
    analysis = Analysis(batch, seq, linear=linear)
    results = analysis.full()

    sites = []
    for enzyme, positions in results.items():
        if positions:
            sites.append(
                {
                    "enzyme": str(enzyme),
                    "positions": positions,
                    "cut_count": len(positions),
                }
            )
    return sorted(sites, key=lambda x: x["enzyme"])


def annotate_from_genbank(filepath: str) -> dict:
    """Read a GenBank file and return features as JSON-serializable dicts."""
    record = SeqIO.read(filepath, "genbank")
    features = []
    for feat in record.features:
        features.append(
            {
                "type": feat.type,
                "location": str(feat.location),
                "start": int(feat.location.start),
                "end": int(feat.location.end),
                "strand": feat.location.strand,
                "qualifiers": {k: v[0] if len(v) == 1 else v for k, v in feat.qualifiers.items()},
            }
        )
    return {
        "name": record.name,
        "description": record.description,
        "length": len(record.seq),
        "topology": record.annotations.get("topology", "unknown"),
        "features": features,
    }
