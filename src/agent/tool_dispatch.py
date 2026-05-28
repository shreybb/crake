"""Tool dispatch: maps Claude tool names to Python function calls.

The `dispatch` function is the single entry point.  It:
1. Calls the appropriate tool function with validated arguments.
2. Stores results in `session` for downstream tools (e.g. export_files
   reads last_assembly / last_validation / last_primers automatically).
3. Returns the result dict (always JSON-serialisable).

No Streamlit imports — fully testable without a running app.
"""
from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

# Tool imports — direct Python calls, no subprocess
from src.tools.fetch_sequence import (
    fetch_by_accession as _fetch_by_accession,
    fetch_from_uniprot as _fetch_from_uniprot,
    search_gene as _search_gene,
)
from src.tools.import_file import import_sequence as _import_sequence
from src.tools.sequence_design import (
    optimize_codons as _optimize_codons,
    suggest_parts_for_host as _suggest_parts,
)
from src.tools.target_site import (
    extract_homology_arms,
    find_crispr_pam_sites,
    find_restriction_edit_sites,
)
from src.tools.primer_design import design_primers as _design_primers
from src.tools.assembly import simulate_gibson, simulate_restriction_ligation
from src.tools.validation import validate_plasmid as _validate_plasmid
from src.tools.gene_introduction import introduce_gene as _introduce_gene
from src.tools.export import (
    write_fasta,
    write_genbank,
    write_plasmid_map,
    write_primers_csv,
    write_protocol_md,
)


def dispatch(tool_name: str, tool_input: dict, session: dict) -> dict:
    """Call the named tool and return its JSON-serialisable result.

    Args:
        tool_name: One of the names defined in tool_definitions.TOOL_DEFINITIONS.
        tool_input: The ``input`` field from the Claude tool_use block.
        session: Mutable session dict (e.g. st.session_state).  Side effects:
            ``last_sequence``, ``last_assembly``, ``last_validation``,
            ``last_primers``, and ``export_paths`` are written here.

    Raises:
        ValueError: If ``tool_name`` is not recognised.
    """
    handlers = {
        "search_gene": _handle_search_gene,
        "fetch_by_accession": _handle_fetch_by_accession,
        "import_sequence": _handle_import_sequence,
        "suggest_parts": _handle_suggest_parts,
        "optimize_codons": _handle_optimize_codons,
        "find_target_sites": _handle_find_target_sites,
        "design_primers": _handle_design_primers,
        "simulate_assembly": _handle_simulate_assembly,
        "validate_plasmid": _handle_validate_plasmid,
        "introduce_gene": _handle_introduce_gene,
        "export_files": _handle_export_files,
    }
    handler = handlers.get(tool_name)
    if handler is None:
        raise ValueError(f"Unknown tool: '{tool_name}'")
    return handler(tool_input, session)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FEAT_COLORS: dict[str, str] = {
    "CDS":           "#4ADE80",   # vivid green
    "gene":          "#86EFAC",   # light green
    "promoter":      "#818CF8",   # indigo
    "terminator":    "#F87171",   # red
    "misc_binding":  "#FCD34D",   # amber
    "rep_origin":    "#C084FC",   # purple
    "regulatory":    "#FB923C",   # orange
    "5'UTR":         "#67E8F9",   # cyan
    "3'UTR":         "#67E8F9",   # cyan
    "misc_feature":  "#94A3B8",   # slate
    "primer_bind":   "#38BDF8",   # sky blue
    "LTR":           "#A78BFA",   # violet
    "enhancer":      "#FF6B6B",   # pink-red
    "exon":          "#10B981",   # emerald
    "intron":        "#6B7280",   # gray
    "sig_peptide":   "#F472B6",   # pink
    "mat_peptide":   "#34D399",   # teal
}
_DEFAULT_FEAT_COLOR = "#818CF8"


def _feat_color(feat_type: str) -> str:
    return _FEAT_COLORS.get(feat_type, _DEFAULT_FEAT_COLOR)


def _result_to_seqviz(result: dict) -> dict | None:
    """Convert a fetch/import result dict to seqviz component data."""
    seq = result.get("sequence", "")
    if not seq or result.get("sequence_type") == "protein":
        return None
    name = (result.get("gene_name") or result.get("accession") or "sequence")[:30]
    annotations = []
    for f in result.get("features", []):
        feat_type = f.get("type", "")
        label = (f.get("product") or f.get("gene") or f.get("name") or "")[:32]
        # Include type prefix when label doesn't already convey it
        if label and feat_type and feat_type.lower() not in label.lower():
            feat_name = f"{feat_type}: {label}"
        elif label:
            feat_name = label
        else:
            feat_name = feat_type or "feature"
        feat_name = feat_name[:48]
        annotations.append({
            "name": feat_name,
            "start": f["start"],
            "end": f["end"],
            "direction": f.get("strand", 1),
            "color": _feat_color(feat_type),
        })
    return {"name": name, "seq": seq, "annotations": annotations}


def _genbank_to_seqviz(gb_path: Path) -> dict | None:
    """Read a GenBank file and return seqviz component data with annotations."""
    try:
        record = SeqIO.read(str(gb_path), "genbank")
        name = (record.name or record.id or "construct")[:30]
        annotations = []
        for feat in record.features:
            if feat.type == "source":
                continue
            q = feat.qualifiers if feat.qualifiers else {}
            raw_label = ""
            for key in ("product", "gene", "label", "note"):
                if key in q:
                    raw_label = q[key][0][:32]
                    break
            if raw_label and feat.type and feat.type.lower() not in raw_label.lower():
                label = f"{feat.type}: {raw_label}"[:48]
            elif raw_label:
                label = raw_label
            else:
                label = feat.type
            annotations.append({
                "name": label,
                "start": int(feat.location.start),
                "end": int(feat.location.end),
                "direction": feat.location.strand if feat.location.strand is not None else 1,
                "color": _feat_color(feat.type),
            })
        return {"name": name, "seq": str(record.seq), "annotations": annotations}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Individual handlers
# ---------------------------------------------------------------------------

def _handle_search_gene(inp: dict, session: dict) -> dict:
    result = _search_gene(
        inp["gene_name"],
        inp["organism"],
        full_sequence=inp.get("full_sequence", False),
    )
    session["last_sequence"] = result
    session["last_seqviz"] = _result_to_seqviz(result)
    return result


def _handle_fetch_by_accession(inp: dict, session: dict) -> dict:
    db = inp.get("db", "nucleotide")
    if db == "uniprot":
        result = _fetch_from_uniprot(inp["accession"])
    else:
        result = _fetch_by_accession(
            inp["accession"],
            db=db,
            full_sequence=inp.get("full_sequence", False),
        )
    if "error" not in result:
        session["last_sequence"] = result
        session["last_seqviz"] = _result_to_seqviz(result)
    return result


def _handle_import_sequence(inp: dict, session: dict) -> dict:
    result = _import_sequence(inp["path"])
    if "error" not in result:
        session["last_sequence"] = result
        session["last_seqviz"] = _result_to_seqviz(result)
    return result


def _handle_suggest_parts(inp: dict, session: dict) -> dict:
    return _suggest_parts(inp["host"])


def _handle_optimize_codons(inp: dict, session: dict) -> dict:
    result = _optimize_codons(inp["sequence"], inp["host"])
    session["last_optimization"] = result
    return result


def _handle_find_target_sites(inp: dict, session: dict) -> dict:
    seq = inp["sequence"]
    method = inp["method"]
    arm_length = inp.get("arm_length", 500)
    topology = inp.get("topology", "linear")

    if method == "restriction":
        sites = find_restriction_edit_sites(seq, arm_length=arm_length, topology=topology)
        return {"method": method, "target_sites": sites, "site_count": len(sites)}

    if method == "crispr":
        pam = inp.get("pam", "NGG")
        sites = find_crispr_pam_sites(seq, pam=pam, arm_length=arm_length)
        return {"method": method, "target_sites": sites, "site_count": len(sites), "pam": pam}

    if method == "homologous":
        position = inp.get("position")
        if position is None:
            return {"error": "position required for homologous method"}
        site = extract_homology_arms(seq, position, arm_length)
        return {"method": method, "target_sites": [site], "recommended_site": site}

    return {"error": f"Unknown method: {method}"}


def _handle_design_primers(inp: dict, session: dict) -> dict:
    result = _design_primers(
        template=inp["template"],
        overhang_fwd=inp.get("overhang_fwd", ""),
        overhang_rev=inp.get("overhang_rev", ""),
        opt_tm=inp.get("opt_tm", 60.0),
    )
    session["last_primers"] = result
    return result


def _handle_simulate_assembly(inp: dict, session: dict) -> dict:
    method = inp["method"]
    fragments = inp["fragments"]

    if method == "gibson":
        result = simulate_gibson(fragments)
    else:
        enzymes = inp.get("enzymes", [])
        result = simulate_restriction_ligation(fragments, enzymes)

    session["last_assembly"] = result
    return result


def _handle_validate_plasmid(inp: dict, session: dict) -> dict:
    result = _validate_plasmid(
        sequence=inp["sequence"],
        name=inp.get("name", "construct"),
        topology=inp.get("topology", "circular"),
    )
    session["last_validation"] = result
    return result


def _handle_introduce_gene(inp: dict, session: dict) -> dict:
    result = _introduce_gene(
        gene_name=inp["gene_name"],
        source_organism=inp["source_organism"],
        target_host=inp["target_host"],
        expression_goal=inp.get("expression_goal", ""),
    )
    if "error" not in result:
        session["last_gene_introduction"] = result
        # Store optimised sequence as the active sequence for downstream tools
        session["last_sequence"] = {
            "gene_name": result["gene"],
            "sequence": result["optimized_sequence"],
            "organism": result["source_organism"],
            "suggested_host": result["target_host"],
        }
    return result


def _handle_export_files(inp: dict, session: dict) -> dict:
    name = inp["name"]
    out_dir = Path(inp.get("output_dir", "./crake_output"))
    out_dir.mkdir(parents=True, exist_ok=True)

    assembly = session.get("last_assembly") or {}
    validation = session.get("last_validation") or {}
    primers = session.get("last_primers") or {}

    paths: dict[str, str] = {}
    sequence = assembly.get("product_sequence", "")

    if sequence:
        gb_path = out_dir / f"{name}.gb"
        write_genbank(assembly, validation, name, gb_path)
        paths["genbank"] = str(gb_path)

        fa_path = out_dir / f"{name}.fa"
        write_fasta(sequence, name, fa_path)
        paths["fasta"] = str(fa_path)

        try:
            svg_path = out_dir / f"{name}_map.svg"
            write_plasmid_map(gb_path, svg_path)
            paths["map"] = str(svg_path)
        except Exception as exc:
            paths["map_error"] = str(exc)

        # Update seqviz with annotated GenBank data (richer than fetch result)
        seqviz = _genbank_to_seqviz(gb_path)
        if seqviz:
            session["last_seqviz"] = seqviz

    primer_pairs = primers.get("primer_pairs", [])
    if primer_pairs:
        csv_path = out_dir / "primers.csv"
        write_primers_csv(primer_pairs, csv_path)
        paths["primers_csv"] = str(csv_path)

    md_path = out_dir / "protocol.md"
    write_protocol_md(assembly, primers, validation, name, md_path)
    paths["protocol"] = str(md_path)

    session["export_paths"] = paths
    return paths
