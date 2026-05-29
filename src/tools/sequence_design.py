#!/usr/bin/env python3
"""
Design and optimize a gene expression cassette.

CLI: ``crake cmd "/suggest e_coli"`` or ``/optimize yeast`` (after loading a sequence).
"""
from __future__ import annotations

from .knowledge import (
    suggest_backbone,
    suggest_promoter,
    suggest_selectable_marker,
    suggest_terminator,
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
    from dnachisel import CodonOptimize, DnaOptimizationProblem, EnforceTranslation

    if len(sequence) % 3 != 0:
        return {"error": "Sequence length must be divisible by 3 (in-frame CDS required)"}

    seq_upper = sequence.upper()
    if not seq_upper.startswith("ATG"):
        return {"error": "Sequence must start with ATG (Met start codon). Provide a complete CDS."}

    # Map Crake hosts to python_codon_tables names (bundled CSVs or NCBI taxon IDs).
    # plant/agrobacterium use taxon 3702 (Arabidopsis thaliana) — T-DNA expresses in plant cells.
    host_map = {
        "e_coli": "e_coli",
        "yeast": "s_cerevisiae_4932",
        "plant_nuclear": "3702",
        "agrobacterium": "3702",
    }
    species = host_map.get(host, "e_coli")

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
