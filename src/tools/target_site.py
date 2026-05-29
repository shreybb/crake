#!/usr/bin/env python3
"""
Identify edit sites within a genomic sequence.

CLI: ``crake cmd "/targets crispr"`` or ``/targets restriction`` (after loading a sequence).
"""
from __future__ import annotations

import re

from Bio.Restriction import Analysis, CommOnly
from Bio.Seq import Seq

DEFAULT_ARM_LENGTH = 500  # bp of flanking sequence extracted on each side

# Minimum guide GC for a viable CRISPR site
_CRISPR_GC_MIN = 40.0
_CRISPR_GC_MAX = 70.0
_CRISPR_MAX_SITES = 20   # cap returned CRISPR sites


def find_restriction_edit_sites(
    sequence: str,
    require_unique: bool = True,
    arm_length: int = DEFAULT_ARM_LENGTH,
    topology: str = "linear",
) -> list[dict]:
    """Find restriction sites suitable as edit entry points.

    Args:
        sequence: DNA sequence to scan.
        require_unique: When True (default), only return enzymes that cut
            exactly once — guaranteeing a defined insertion point.
        arm_length: Length of flanking sequence to include as ``left_arm``
            / ``right_arm`` for downstream assembly.
        topology: ``"circular"`` or ``"linear"`` (default).  Use ``"circular"``
            when scanning a plasmid map to detect sites that span the sequence
            origin; use ``"linear"`` for genomic loci or PCR products.

    Returns:
        List of site dicts sorted by position, each containing the enzyme
        name, cut position, overhang size, and flanking arms.
    """
    seq = Seq(sequence.upper())
    analysis = Analysis(CommOnly, seq, linear=(topology != "circular"))
    results = analysis.full()

    sites = []
    for enzyme, positions in results.items():
        if not positions:
            continue
        if require_unique and len(positions) != 1:
            continue
        pos = positions[0]
        sites.append({
            "enzyme": str(enzyme),
            "position": pos,
            "overhang_bp": enzyme.ovhg,
            "cut_count": len(positions),
            "left_arm": sequence[max(0, pos - arm_length): pos].upper(),
            "right_arm": sequence[pos: pos + arm_length].upper(),
            "arm_length_bp": arm_length,
        })

    return sorted(sites, key=lambda x: x["position"])


def extract_homology_arms(
    sequence: str,
    position: int,
    arm_length: int = DEFAULT_ARM_LENGTH,
) -> dict:
    """Extract left and right homology arms centred on ``position``.

    Suitable for designing HR donor constructs.  The arms are ready to be
    used as ``--parts`` inputs to ``assembly --method gibson``.

    Returns a single site dict with ``left_arm`` and ``right_arm``.
    """
    seq = sequence.upper()
    left_start = max(0, position - arm_length)
    right_end = min(len(seq), position + arm_length)

    return {
        "method": "homologous",
        "position": position,
        "left_arm": seq[left_start:position],
        "right_arm": seq[position:right_end],
        "left_arm_length_bp": position - left_start,
        "right_arm_length_bp": right_end - position,
        "arm_length_bp": arm_length,
    }


def _gc_percent(seq: str) -> float:
    if not seq:
        return 0.0
    gc = seq.upper().count("G") + seq.upper().count("C")
    return round(gc / len(seq) * 100, 1)


def _has_homopolymer(seq: str, run: int = 5) -> bool:
    """Return True if any single base is repeated ``run`` or more times."""
    return bool(re.search(r"([ATCG])\1{" + str(run - 1) + r"}", seq.upper()))


def find_crispr_pam_sites(
    sequence: str,
    pam: str = "NGG",
    arm_length: int = DEFAULT_ARM_LENGTH,
) -> list[dict]:
    """Scan both strands for CRISPR PAM sites.

    Filters out guides with:
    - GC content outside [40%, 70%]
    - Homopolymer runs of 5+ bases

    Returns up to ``_CRISPR_MAX_SITES`` sites, ranked by GC closest to 55%.

    Args:
        sequence: Genomic DNA to scan.
        pam: PAM sequence; ``N`` matches any base.  Default ``NGG`` (SpCas9).
        arm_length: Flanking arm length included in each site dict.
    """
    seq_upper = sequence.upper()
    rev_comp = str(Seq(seq_upper).reverse_complement())
    pam_regex = pam.replace("N", "[ATCG]")
    pattern = re.compile(r"(?=([ATCG]{20}" + pam_regex + r"))")

    sites: list[dict] = []

    for strand, s in ((1, seq_upper), (-1, rev_comp)):
        for match in pattern.finditer(s):
            full_site = match.group(1)
            guide = full_site[:20]
            gc = _gc_percent(guide)

            if not (_CRISPR_GC_MIN <= gc <= _CRISPR_GC_MAX):
                continue
            if _has_homopolymer(guide):
                continue

            pos = match.start()
            if strand == -1:
                # Map reverse-complement position back to forward strand.
                # pos_fwd is the 5' end of the full 23-nt site (NCC + protospacer
                # complement) on the forward strand.
                pos = len(seq_upper) - pos - len(full_site)
                # SpCas9 blunt cut: 3 nt upstream of PAM in the protospacer.
                # For a reverse-strand guide the PAM complement (NCC) is at the
                # 5' end of the mapped site, so the cut falls at pos+5/pos+6
                # on the forward strand.
                cut_position = pos + 6
            else:
                # Forward strand: protospacer at pos..pos+20, PAM at pos+20..pos+23.
                # Cas9 cuts between guide positions 17 and 18 (3 nt from PAM).
                cut_position = pos + 17

            guide_rna = guide.replace("T", "U")
            sites.append({
                "strand": strand,
                "position": pos,
                "cut_position": cut_position,   # actual SpCas9 blunt-cut locus (forward-strand coord)
                "protospacer": guide,            # DNA sequence (order as oligo)
                "guide_rna": guide_rna,          # RNA sequence (T→U; for sgRNA synthesis)
                "pam": full_site[20:],
                "gc_percent": gc,
                "left_arm": seq_upper[max(0, pos - arm_length): pos],
                "right_arm": seq_upper[pos: pos + arm_length],
                "arm_length_bp": arm_length,
            })

    # Rank by GC closest to 55% (optimal for SpCas9 efficiency)
    sites.sort(key=lambda x: abs(x["gc_percent"] - 55.0))
    return sites[:_CRISPR_MAX_SITES]


def recommend_edit_site(sites: list[dict]) -> dict | None:
    """Return the first (best-ranked) site from the list, or None."""
    return sites[0] if sites else None
