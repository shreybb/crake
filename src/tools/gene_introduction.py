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


def _build_next_steps(host: str, vector_name: str, marker_name: str) -> list[str]:
    steps = [
        f"1. Synthesise or amplify the codon-optimised CDS.",
        f"2. Clone into {vector_name} (e.g. Gibson Assembly or restriction-ligation).",
        f"3. Transform into appropriate {host} strain.",
        f"4. Select transformants on media with {marker_name} selection.",
        f"5. Verify insertion by colony PCR and Sanger sequencing.",
        f"6. Induce/confirm expression by western blot or assay.",
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

    # Step 3 — suggest parts (take first suggestion from each list)
    backbones = suggest_backbone(target_host)
    promoters = suggest_promoter(target_host)
    terminators = suggest_terminator(target_host)
    markers = suggest_selectable_marker(target_host)

    vector = backbones[0] if backbones else {"name": "unknown"}
    promoter = promoters[0] if promoters else {"name": "unknown"}
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
