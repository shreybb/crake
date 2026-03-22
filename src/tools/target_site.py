#!/usr/bin/env python3
"""
Identify edit sites within a genomic sequence.

Usage:
    python src/tools/target_site.py --sequence ATCG... --method restriction
    python src/tools/target_site.py --sequence ATCG... --method homologous --position 500
    python src/tools/target_site.py --sequence ATCG... --method crispr
    python src/tools/target_site.py --file locus.gb --method restriction

Methods:
    restriction  — find unique restriction enzyme sites (single-cutter preferred)
    homologous   — extract left/right homology arms around a given position
    crispr       — scan for SpCas9 NGG PAM sites on both strands

Outputs JSON.  The ``left_arm`` / ``right_arm`` in each site feed directly into:
    assembly --method gibson --parts <left_arm_file> <insert_file> <right_arm_file>
    primer_design --template <left_arm>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from Bio import SeqIO
from Bio.Restriction import CommOnly, Analysis
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
) -> list[dict]:
    """Find restriction sites suitable as edit entry points.

    Args:
        sequence: DNA sequence to scan.
        require_unique: When True (default), only return enzymes that cut
            exactly once — guaranteeing a defined insertion point.
        arm_length: Length of flanking sequence to include as ``left_arm``
            / ``right_arm`` for downstream assembly.

    Returns:
        List of site dicts sorted by position, each containing the enzyme
        name, cut position, overhang size, and flanking arms.
    """
    seq = Seq(sequence.upper())
    analysis = Analysis(CommOnly, seq, linear=True)
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
                # Map reverse-complement position back to forward strand
                pos = len(seq_upper) - pos - len(full_site)

            guide_rna = guide.replace("T", "U")
            sites.append({
                "strand": strand,
                "position": pos,
                "protospacer": guide,        # DNA sequence (order as oligo)
                "guide_rna": guide_rna,      # RNA sequence (T→U; for sgRNA synthesis)
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Identify edit sites in a genomic DNA sequence"
    )
    seq_group = parser.add_mutually_exclusive_group(required=True)
    seq_group.add_argument("--sequence", help="Raw DNA sequence string")
    seq_group.add_argument("--file", help="GenBank (.gb/.gbk) or FASTA (.fa/.fasta) file")

    parser.add_argument(
        "--method",
        required=True,
        choices=["restriction", "homologous", "crispr"],
        help="Edit strategy to use",
    )
    parser.add_argument(
        "--position",
        type=int,
        default=None,
        help="Desired edit position (required for --method homologous)",
    )
    parser.add_argument(
        "--arm-length",
        type=int,
        default=DEFAULT_ARM_LENGTH,
        help=f"Homology arm length in bp (default {DEFAULT_ARM_LENGTH})",
    )
    parser.add_argument(
        "--pam",
        default="NGG",
        help="PAM sequence for CRISPR scanning (default NGG for SpCas9)",
    )
    parser.add_argument(
        "--allow-multi-cut",
        action="store_true",
        help="Include restriction enzymes that cut more than once (restriction method only)",
    )
    args = parser.parse_args()

    if args.file:
        p = Path(args.file)
        fmt = "genbank" if p.suffix in (".gb", ".gbk") else "fasta"
        record = SeqIO.read(str(p), fmt)
        sequence = str(record.seq).upper()
        seq_name = record.name
    else:
        sequence = args.sequence.upper()
        seq_name = "input"

    result: dict = {
        "name": seq_name,
        "input_length_bp": len(sequence),
        "method": args.method,
    }

    if args.method == "restriction":
        sites = find_restriction_edit_sites(
            sequence,
            require_unique=not args.allow_multi_cut,
            arm_length=args.arm_length,
        )
        result["target_sites"] = sites
        result["recommended_site"] = recommend_edit_site(sites)
        result["site_count"] = len(sites)

    elif args.method == "homologous":
        if args.position is None:
            print(json.dumps({"error": "--position required for --method homologous"}))
            sys.exit(1)
        site = extract_homology_arms(sequence, args.position, args.arm_length)
        result["target_sites"] = [site]
        result["recommended_site"] = site

    elif args.method == "crispr":
        sites = find_crispr_pam_sites(sequence, pam=args.pam, arm_length=args.arm_length)
        result["target_sites"] = sites
        result["recommended_site"] = recommend_edit_site(sites)
        result["site_count"] = len(sites)
        result["pam"] = args.pam

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
