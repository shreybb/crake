"""Orchestrate gene introduction into a target host.

High-level function `introduce_gene` ties together:
  - NCBI sequence fetch (search_gene)
  - Codon optimisation (optimize_codons)
  - Part suggestions (suggest_backbone / suggest_promoter / suggest_terminator /
    suggest_selectable_marker)

Returns a structured JSON-serialisable result ready for the agent to present.
"""
from __future__ import annotations

from src.tools.fetch_sequence import search_gene
from src.tools.knowledge import (
    suggest_backbone,
    suggest_promoter,
    suggest_selectable_marker,
    suggest_terminator,
)
from src.tools.sequence_design import optimize_codons


_VALID_HOSTS = {"e_coli", "yeast", "plant_nuclear"}

# Keywords that signal a desired expression regulation type.
_CONSTITUTIVE_KEYWORDS = {"constitutive", "constant", "stable", "gpd", "tdh3", "tef1", "adh1"}
_INDUCIBLE_KEYWORDS = {
    "inducible", "induction", "induced", "galactose", "gal1", "gal10",
    "iptg", "arabinose", "copper", "cup1", "methionine", "tetracycline",
}


def _infer_expression_type(expression_goal: str) -> str | None:
    """Parse expression_goal string and return 'constitutive', 'inducible', or None."""
    lower = expression_goal.lower()
    words = set(lower.replace("-", " ").split())
    if words & _CONSTITUTIVE_KEYWORDS:
        return "constitutive"
    if words & _INDUCIBLE_KEYWORDS:
        return "inducible"
    return None


def _pick_promoter(promoters: list[dict], expression_type: str | None) -> dict | None:
    """Select the most appropriate promoter from a list.

    Filters by expression_type if provided; falls back to the first item
    when no match is found.  Returns None if the list is empty.
    """
    if not promoters:
        return None
    if expression_type is None:
        return promoters[0]
    matches = [p for p in promoters if p.get("expression_type") == expression_type]
    return matches[0] if matches else promoters[0]


def _build_cassette_description(
    gene: str,
    host: str,
    promoter_name: str,
    terminator_name: str,
    vector_name: str,
    marker_name: str,
    expression_goal: str,
) -> str:
    goal_clause = f" for {expression_goal}" if expression_goal else ""
    return (
        f"Expression cassette: {promoter_name}::{gene}::{terminator_name} "
        f"cloned into {vector_name} with {marker_name} selection "
        f"for expression in {host}{goal_clause}."
    )


_YEAST_MARKER_STRAIN = {
    "URA3": "ura3Δ (e.g. BY4741, W303-1A, CEN.PK2-1C)",
    "LEU2": "leu2Δ (e.g. BY4741, W303-1A)",
    "HIS3": "his3Δ (e.g. BY4741, W303-1A)",
    "TRP1": "trp1Δ (e.g. BY4741)",
    "kanMX": "any strain (dominant marker; select on YPD + G418 200–400 mg/L)",
    "hygMX": "any strain (dominant marker; select on YPD + Hygromycin B 300 mg/L)",
}


def _build_next_steps(host: str, vector_name: str, marker_name: str) -> list[str]:
    if host == "yeast":
        strain_note = _YEAST_MARKER_STRAIN.get(
            marker_name,
            f"strain auxotrophic for {marker_name} (or use a dominant marker strain)"
        )
        return [
            "1. Synthesise or amplify the codon-optimised CDS.",
            f"2. Clone into {vector_name} upstream of the selected promoter "
            "   (Gibson Assembly or restriction-ligation into MCS).",
            f"3. Transform using the lithium acetate / PEG / ssDNA method into {strain_note}.",
            f"4. Select transformants on appropriate drop-out (SC - {marker_name}) or antibiotic plates.",
            "5. Verify plasmid presence by colony PCR and Sanger sequencing.",
            "6. If using GAL1/GAL10 promoter: grow in SC-glucose first, then induce by "
            "   shifting to SC-galactose (2%) for 4–6 h before assaying expression.",
        ]

    steps = [
        "1. Synthesise or amplify the codon-optimised CDS.",
        f"2. Clone into {vector_name} (e.g. Gibson Assembly or restriction-ligation).",
        f"3. Transform into appropriate {host} strain.",
        f"4. Select transformants on media with {marker_name} selection.",
        "5. Verify insertion by colony PCR and Sanger sequencing.",
        "6. Induce/confirm expression by western blot or assay.",
    ]
    return steps


def introduce_gene(
    gene_name: str,
    source_organism: str,
    target_host: str,
    expression_goal: str = "",
) -> dict:
    """Orchestrate gene introduction into *target_host*.

    Steps:
    1. Fetch CDS from NCBI via search_gene.
    2. Codon-optimise for target_host.
    3. Suggest vector, promoter, terminator, selectable marker.
    4. Assemble and return a structured result.

    Args:
        gene_name: Gene to introduce, e.g. ``"GFP"``.
        source_organism: Source organism, e.g. ``"Aequorea victoria"``.
        target_host: Destination host — one of ``e_coli``, ``yeast``,
            ``plant_nuclear``.
        expression_goal: Optional free-text goal, e.g. ``"fluorescence reporter"``.

    Returns:
        JSON-serialisable dict with keys: gene, source_organism, target_host,
        original_sequence, optimized_sequence, vector, promoter, terminator,
        marker, cassette_description, next_steps.  On error, returns
        ``{"error": "..."}`` with available partial data.
    """
    if target_host not in _VALID_HOSTS:
        return {
            "error": (
                f"Unsupported target_host '{target_host}'. "
                f"Valid options: {sorted(_VALID_HOSTS)}"
            ),
            "gene": gene_name,
            "target_host": target_host,
        }

    # Step 1 — fetch CDS
    fetch_result = search_gene(gene_name, source_organism)
    if "error" in fetch_result:
        return {
            "error": f"Gene fetch failed: {fetch_result['error']}",
            "gene": gene_name,
            "source_organism": source_organism,
            "target_host": target_host,
        }

    original_sequence = fetch_result.get("sequence", "")
    if not original_sequence:
        return {
            "error": "No sequence returned from NCBI.",
            "gene": gene_name,
            "source_organism": source_organism,
            "target_host": target_host,
        }

    # Step 2 — codon optimise
    optimized_sequence = original_sequence
    codon_result = optimize_codons(original_sequence, target_host)
    if "error" not in codon_result:
        optimized_sequence = codon_result.get("optimized_sequence", original_sequence)

    # Step 3 — suggest parts
    backbones = suggest_backbone(target_host)
    promoters = suggest_promoter(target_host)
    terminators = suggest_terminator(target_host)
    markers = suggest_selectable_marker(target_host)

    expression_type = _infer_expression_type(expression_goal)

    vector = backbones[0] if backbones else {"name": "unknown"}
    promoter = _pick_promoter(promoters, expression_type) or {"name": "unknown"}
    terminator = terminators[0] if terminators else {"name": "unknown"}
    marker = markers[0] if markers else {"name": "unknown"}

    vector_name = vector["name"]
    promoter_name = promoter["name"]
    terminator_name = terminator["name"]
    marker_name = marker["name"]

    # Step 4 — assemble result
    cassette_description = _build_cassette_description(
        gene=gene_name,
        host=target_host,
        promoter_name=promoter_name,
        terminator_name=terminator_name,
        vector_name=vector_name,
        marker_name=marker_name,
        expression_goal=expression_goal,
    )

    return {
        "gene": gene_name,
        "source_organism": source_organism,
        "target_host": target_host,
        "expression_goal": expression_goal,
        "original_sequence": original_sequence,
        "optimized_sequence": optimized_sequence,
        "vector": vector,
        "promoter": promoter,
        "terminator": terminator,
        "marker": marker,
        "cassette_description": cassette_description,
        "next_steps": _build_next_steps(target_host, vector_name, marker_name),
    }
