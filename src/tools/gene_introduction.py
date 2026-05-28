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


_VALID_HOSTS = {"e_coli", "yeast", "plant_nuclear", "agrobacterium"}

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


def _pick_backbone(
    backbones: list[dict],
    host: str,
    expression_type: str | None,
) -> dict | None:
    """Select the most appropriate vector backbone.

    For yeast, applies copy-number and pre-loaded promoter heuristics:
    - inducible  → prefer pYES2 (GAL1 pre-loaded, 2-micron); fall back to any
                   high-copy 2-micron vector.
    - constitutive → prefer a high-copy (2-micron) promoter-less vector such as
                     pRS416 so the chosen constitutive promoter is the one inserted.
    - None       → return the first backbone (conservative default).

    For non-yeast hosts the first backbone is returned; part selection there is
    simpler (E. coli: pET-28a; plant binary: pCAMBIA1305.1 are already good defaults).
    """
    if not backbones:
        return None

    if host != "yeast" or expression_type is None:
        return backbones[0]

    if expression_type == "inducible":
        # pYES2 has GAL1 promoter pre-loaded — ideal for galactose-inducible expression.
        for bb in backbones:
            if bb.get("name") == "pYES2":
                return bb
        # Fall back to any high-copy 2-micron vector.
        for bb in backbones:
            if bb.get("copy_number") == "high":
                return bb

    elif expression_type == "constitutive":
        # High-copy (2-micron) without a pre-loaded promoter: the researcher inserts
        # their own constitutive cassette (TEF1, TDH3, etc.) from promoter selection.
        for bb in backbones:
            if bb.get("copy_number") == "high" and "GAL" not in bb.get("promoter", ""):
                return bb

    return backbones[0]


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

# Correct selection media for each yeast marker.
# Auxotrophic markers use SC dropout named after the NUTRIENT omitted (SC-URA, not SC-URA3).
# Dominant antibiotic markers use rich media (YPD) + antibiotic — no SC dropout applies.
_YEAST_SELECTION_MEDIA = {
    "URA3":  "SC-URA (synthetic complete medium lacking uracil)",
    "LEU2":  "SC-LEU (lacking leucine)",
    "HIS3":  "SC-HIS (lacking histidine)",
    "TRP1":  "SC-TRP (lacking tryptophan)",
    "kanMX": "YPD + G418 (200–400 mg/L)",
    "hygMX": "YPD + Hygromycin B (300 mg/L)",
}


def _build_next_steps(host: str, vector_name: str, marker_name: str) -> list[str]:
    if host == "yeast":
        strain_note = _YEAST_MARKER_STRAIN.get(
            marker_name,
            f"strain auxotrophic for {marker_name} (or use a dominant marker strain)"
        )
        selection_media = _YEAST_SELECTION_MEDIA.get(
            marker_name,
            f"SC-{marker_name[:3].upper()} drop-out (lacking the corresponding nutrient)",
        )
        return [
            "1. Synthesise or amplify the codon-optimised CDS.",
            f"2. Clone into {vector_name} upstream of the selected promoter "
            "   (Gibson Assembly or restriction-ligation into MCS).",
            f"3. Transform using the lithium acetate / PEG / ssDNA method into {strain_note}.",
            f"4. Select transformants on {selection_media}.",
            "5. Verify plasmid presence by colony PCR and Sanger sequencing.",
            "6. If using GAL1/GAL10 promoter: grow in SC-glucose first, then induce by "
            "   shifting to SC-galactose (2%) for 4–6 h before assaying expression.",
        ]

    if host in ("agrobacterium", "plant_nuclear"):
        return [
            "1. Synthesise or amplify the codon-optimised CDS (codon usage: Arabidopsis thaliana).",
            f"2. Clone into binary vector {vector_name} (T-DNA left/right borders must flank insert).",
            "3. Transform binary vector into Agrobacterium tumefaciens LBA4404 or GV3101 "
            "   (electroporation or freeze-thaw method); select on kanamycin or spectinomycin.",
            "4. Infect plant tissue: leaf-disc co-cultivation or vacuum-infiltration "
            "   (Agrobacterium-mediated transformation).",
            f"5. Select transformed calli/plants on shoot-induction medium + {marker_name} "
            "   selection (kanamycin 100 mg/L or hygromycin 25 mg/L).",
            "6. Regenerate T0 plantlets; transfer to rooting medium.",
            "7. Confirm T-DNA integration by PCR on genomic DNA (use primers spanning T-DNA borders).",
            "8. Grow T0 to seed; select T1 segregants (3:1 ratio indicates single-locus insertion).",
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

    vector = _pick_backbone(backbones, target_host, expression_type) or {"name": "unknown"}
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
