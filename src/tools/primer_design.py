#!/usr/bin/env python3
"""
Design PCR primers for a template sequence.

CLI: ``crake cmd "/primers"`` or ``/primers ATTB1 ATTB2`` (after loading a sequence).
"""
from __future__ import annotations

import primer3


def design_primers(
    template: str,
    overhang_fwd: str = "",
    overhang_rev: str = "",
    product_min_size: int = 100,
    product_max_size: int | None = None,
    opt_tm: float = 60.0,
) -> dict:
    """Design primers for a template, optionally with Gibson assembly overhangs."""
    product_max_size = product_max_size or len(template) + 50

    result = primer3.design_primers(
        seq_args={
            "SEQUENCE_ID": "target",
            "SEQUENCE_TEMPLATE": template,
        },
        global_args={
            "PRIMER_OPT_SIZE": 20,
            "PRIMER_MIN_SIZE": 18,
            "PRIMER_MAX_SIZE": 27,
            "PRIMER_OPT_TM": opt_tm,
            "PRIMER_MIN_TM": opt_tm - 5,
            "PRIMER_MAX_TM": opt_tm + 5,
            "PRIMER_MIN_GC": 40.0,
            "PRIMER_MAX_GC": 70.0,
            "PRIMER_PRODUCT_SIZE_RANGE": [[product_min_size, product_max_size]],
            "PRIMER_NUM_RETURN": 3,
        },
    )

    pairs = []
    num_returned = result.get("PRIMER_PAIR_NUM_RETURNED", 0)
    for i in range(num_returned):
        fwd_seq = result[f"PRIMER_LEFT_{i}_SEQUENCE"]
        rev_seq = result[f"PRIMER_RIGHT_{i}_SEQUENCE"]
        pairs.append({
            "rank": i,
            "forward": {
                "binding_region": fwd_seq,
                "full_sequence": overhang_fwd + fwd_seq,
                "tm_celsius": round(result[f"PRIMER_LEFT_{i}_TM"], 1),
                "gc_percent": round(result[f"PRIMER_LEFT_{i}_GC_PERCENT"], 1),
                "length": len(overhang_fwd + fwd_seq),
            },
            "reverse": {
                "binding_region": rev_seq,
                "full_sequence": overhang_rev + rev_seq,
                "tm_celsius": round(result[f"PRIMER_RIGHT_{i}_TM"], 1),
                "gc_percent": round(result[f"PRIMER_RIGHT_{i}_GC_PERCENT"], 1),
                "length": len(overhang_rev + rev_seq),
            },
            "product_size_bp": result[f"PRIMER_PAIR_{i}_PRODUCT_SIZE"],
            "penalty": round(result[f"PRIMER_PAIR_{i}_PENALTY"], 3),
        })

    warning = None
    if not pairs:
        template_gc = round(gc_content(template), 1)
        warning = (
            f"No primer pairs found (template GC {template_gc}%). "
            "Try widening the product size range or adjusting the Tm window."
        )

    return {
        "template_length": len(template),
        "primer_pairs": pairs,
        "warning": warning,
        "overhangs_applied": {
            "forward": overhang_fwd,
            "reverse": overhang_rev,
        },
    }


def gc_content(seq: str) -> float:
    seq = seq.upper()
    gc = seq.count("G") + seq.count("C")
    return round(gc / len(seq) * 100, 1) if seq else 0.0


def melting_temperature(seq: str) -> float:
    """Nearest-neighbor Tm via primer3-py."""
    return round(primer3.calc_tm(seq), 1)
