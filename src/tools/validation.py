#!/usr/bin/env python3
"""
Validate a plasmid construct: ORF check, GC content, restriction map.

CLI: ``crake cmd "/validate"`` (after loading a sequence).
"""

from __future__ import annotations

from Bio.Restriction import Analysis, CommOnly
from Bio.Seq import Seq


def find_orfs(sequence: str, min_length: int = 100) -> list[dict]:
    """Find open reading frames >= min_length codons."""
    seq = Seq(sequence.upper())
    orfs = []
    for strand, nuc in [(1, seq), (-1, seq.reverse_complement())]:
        for frame in range(3):
            subseq = nuc[frame:]
            remainder = len(subseq) % 3
            subseq = subseq[:-remainder] if remainder else subseq
            trans = str(subseq.translate())
            aa_start = 0
            while True:
                m_pos = trans.find("M", aa_start)
                if m_pos == -1:
                    break
                stop_pos = trans.find("*", m_pos)
                if stop_pos == -1:
                    break
                length_aa = stop_pos - m_pos
                if length_aa >= min_length:
                    start_nt = frame + m_pos * 3
                    end_nt = frame + stop_pos * 3 + 3
                    if strand == -1:
                        start_nt, end_nt = len(sequence) - end_nt, len(sequence) - start_nt
                    orfs.append(
                        {
                            "strand": strand,
                            "frame": frame,
                            "start_nt": start_nt,
                            "end_nt": end_nt,
                            "length_aa": length_aa,
                            "length_bp": length_aa * 3,
                        }
                    )
                aa_start = m_pos + 1
    return sorted(orfs, key=lambda x: -x["length_aa"])


def gc_windows(sequence: str, window: int = 100) -> dict:
    """GC content in sliding windows — flags regions > 70% or < 30%."""
    seq = sequence.upper()
    issues = []
    for i in range(0, len(seq) - window, window // 2):
        chunk = seq[i : i + window]
        gc = (chunk.count("G") + chunk.count("C")) / len(chunk) * 100
        if gc > 70 or gc < 30:
            issues.append(
                {
                    "start": i,
                    "end": i + window,
                    "gc_percent": round(gc, 1),
                    "flag": "high_gc" if gc > 70 else "low_gc",
                }
            )
    return {
        "overall_gc_percent": round((seq.count("G") + seq.count("C")) / len(seq) * 100, 2)
        if seq
        else 0,
        "flagged_windows": issues,
    }


def restriction_map(sequence: str, linear: bool = False) -> list[dict]:
    """Common restriction enzyme sites.

    Args:
        sequence: DNA sequence to analyse.
        linear: When True, treat the sequence as linear (e.g. a PCR product or
            restriction-digested backbone).  When False (default), treat as
            circular (standard plasmid).
    """
    seq = Seq(sequence.upper())
    analysis = Analysis(CommOnly, seq, linear=linear)
    results = analysis.full()
    sites = []
    for enzyme, positions in results.items():
        if positions:
            sites.append(
                {
                    "enzyme": str(enzyme),
                    "positions": positions,
                    "count": len(positions),
                }
            )
    return sorted(sites, key=lambda x: x["enzyme"])


def validate_plasmid(
    sequence: str,
    name: str = "construct",
    topology: str = "circular",
) -> dict:
    """Run all validation checks on a plasmid sequence."""
    orfs = find_orfs(sequence)
    gc = gc_windows(sequence)
    rsites = restriction_map(sequence, linear=(topology == "linear"))

    warnings = []
    if not orfs:
        warnings.append("No ORFs found (>= 100 aa). Is this an expression construct?")
    if gc["overall_gc_percent"] > 65:
        warnings.append(f"High overall GC content: {gc['overall_gc_percent']}%")
    if gc["overall_gc_percent"] < 35:
        warnings.append(f"Low overall GC content: {gc['overall_gc_percent']}%")
    if len(gc["flagged_windows"]) > 5:
        warnings.append(f"{len(gc['flagged_windows'])} windows with extreme GC content")

    return {
        "name": name,
        "length_bp": len(sequence),
        "topology": topology,
        "gc_analysis": gc,
        "orfs": orfs[:10],  # top 10 by length
        "restriction_sites": rsites,
        "warnings": warnings,
        "passed_checks": len(warnings) == 0,
    }
