#!/usr/bin/env python3
"""
Design and optimize a gene expression cassette.

Usage:
    python src/tools/sequence_design.py --host e_coli [--suggest-parts]
    python src/tools/sequence_design.py --optimize-codons --sequence ATCG... --host e_coli
    python src/tools/sequence_design.py --gc-analysis --sequence ATCG...

Outputs JSON.
"""
from __future__ import annotations
import argparse
import json
import sys

from .knowledge import (
    suggest_backbone, suggest_promoter,
    suggest_terminator, suggest_selectable_marker,
)


def analyze_sequence(sequence: str) -> dict:
    """Basic sequence statistics."""
    seq = sequence.upper()
    length = len(seq)
    gc = seq.count("G") + seq.count("C")
    return {
        "length_bp": length,
        "gc_content_percent": round(gc / length * 100, 2) if length else 0,
        "at_content_percent": round((seq.count("A") + seq.count("T")) / length * 100, 2) if length else 0,
        "base_counts": {
            "A": seq.count("A"),
            "T": seq.count("T"),
            "G": seq.count("G"),
            "C": seq.count("C"),
            "N": seq.count("N"),
        },
    }


def optimize_codons(sequence: str, host: str) -> dict:
    """
    Codon-optimize a coding sequence for the target host using DNA Chisel.
    Input sequence must start with ATG and be in-frame (length % 3 == 0).
    """
    from dnachisel import DnaOptimizationProblem, CodonOptimize, EnforceTranslation

    if len(sequence) % 3 != 0:
        return {"error": "Sequence length must be divisible by 3 (in-frame CDS required)"}

    seq_upper = sequence.upper()
    if not seq_upper.startswith("ATG"):
        return {"error": "Sequence must start with ATG (Met start codon). Provide a complete CDS."}

    # Map host names to python_codon_tables species names
    host_map = {
        "e_coli": "Escherichia coli general",
        "yeast": "Saccharomyces cerevisiae",
        "plant_nuclear": "Arabidopsis thaliana",
        "agrobacterium": "Arabidopsis thaliana",  # optimize for plant nuclear expression
    }
    species = host_map.get(host, "Escherichia coli general")

    problem = DnaOptimizationProblem(
        sequence=sequence,
        constraints=[EnforceTranslation()],
        objectives=[CodonOptimize(species=species)],
    )

    gc_before = analyze_sequence(sequence)["gc_content_percent"]
    try:
        problem.resolve_constraints()
        problem.optimize()
        optimized = problem.sequence
        gc_after = analyze_sequence(optimized)["gc_content_percent"]
        return {
            "original_sequence": sequence,
            "optimized_sequence": optimized,
            "host": host,
            "species_table": species,
            "length_bp": len(optimized),
            "gc_before": gc_before,
            "gc_after": gc_after,
            "analysis": analyze_sequence(optimized),
        }
    except Exception as exc:
        return {"error": str(exc), "original_sequence": sequence}


def suggest_parts_for_host(host: str) -> dict:
    """Return recommended parts (backbone, promoter, terminator, marker) for the host."""
    return {
        "host": host,
        "recommended_backbones": suggest_backbone(host),
        "recommended_promoters": suggest_promoter(host),
        "recommended_terminators": suggest_terminator(host),
        "recommended_selectable_markers": suggest_selectable_marker(host),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sequence design and codon optimization")
    parser.add_argument("--host", default="e_coli",
                        choices=["e_coli", "yeast", "plant_nuclear", "agrobacterium"],
                        help="Target host organism")
    parser.add_argument("--suggest-parts", action="store_true",
                        help="Suggest backbones, promoters, terminators for the host")
    parser.add_argument("--optimize-codons", action="store_true",
                        help="Codon-optimize the provided sequence")
    parser.add_argument("--gc-analysis", action="store_true",
                        help="Run basic GC/length analysis on a sequence")
    parser.add_argument("--sequence", default="",
                        help="Input DNA sequence (for --optimize-codons or --gc-analysis)")
    args = parser.parse_args()

    output: dict = {}

    if args.suggest_parts:
        output = suggest_parts_for_host(args.host)
    elif args.optimize_codons:
        if not args.sequence:
            print(json.dumps({"error": "--sequence required for --optimize-codons"}))
            sys.exit(1)
        output = optimize_codons(args.sequence, args.host)
    elif args.gc_analysis:
        if not args.sequence:
            print(json.dumps({"error": "--sequence required for --gc-analysis"}))
            sys.exit(1)
        output = analyze_sequence(args.sequence)
    else:
        parser.print_help()
        sys.exit(0)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
