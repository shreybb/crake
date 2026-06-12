"""Offline hero demo: GFP CDS → e_coli optimize → validate → primers → lab export.

No network, no Streamlit. Used by ``crake hero`` and CI golden tests.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.agent.tool_dispatch import dispatch

# Same CDS as tests/unit/test_golden_gfp_chain.py (Aequorea GFP, valid ORF).
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "examples" / "hero"
DEFAULT_CONSTRUCT_NAME = "pHeroGFP"


def run_hero_workflow(
    output_dir: Path,
    *,
    data_dir: Path | None = None,
    construct_name: str = DEFAULT_CONSTRUCT_NAME,
) -> dict[str, Any]:
    """Run the hero pipeline and write export artifacts under *output_dir*.

    Returns a manifest dict (also suitable for golden regression).
    """
    data_dir = data_dir or DEFAULT_DATA_DIR
    gfp_fa = data_dir / "gfp_cds.fa"
    if not gfp_fa.is_file():
        raise FileNotFoundError(f"Hero input not found: {gfp_fa}")

    session: dict = {}
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    imp = dispatch("import_sequence", {"path": str(gfp_fa)}, session)
    if imp.get("error"):
        raise RuntimeError(imp["error"])

    opt = dispatch(
        "optimize_codons",
        {"sequence": session["last_sequence"]["sequence"], "host": "e_coli"},
        session,
    )
    if opt.get("error"):
        raise RuntimeError(opt["error"])

    opt_seq = session["last_sequence"]["sequence"]

    val = dispatch(
        "validate_plasmid",
        {"sequence": opt_seq, "name": construct_name, "topology": "linear"},
        session,
    )
    if val.get("error"):
        raise RuntimeError(val["error"])

    prim = dispatch("design_primers", {"template": opt_seq}, session)
    if prim.get("error"):
        raise RuntimeError(prim["error"])

    paths = dispatch(
        "export_files",
        {
            "name": construct_name,
            "output_dir": str(out_dir),
            "allow_sequence_only": True,
        },
        session,
    )
    if paths.get("error"):
        raise RuntimeError(paths["error"])

    return build_export_manifest(out_dir, construct_name, session, paths)


def build_export_manifest(
    output_dir: Path,
    construct_name: str,
    session: dict,
    export_paths: dict,
) -> dict[str, Any]:
    """Summarize export bundle for golden tests (stable across dates in GenBank/protocol)."""
    fasta_path = Path(export_paths["fasta"])
    sequence = fasta_path.read_text().splitlines()
    seq_lines = [ln for ln in sequence if not ln.startswith(">")]
    seq = "".join(seq_lines).strip().upper()

    opt = session.get("last_optimization") or {}
    val = session.get("last_validation") or {}
    prim = session.get("last_primers") or {}

    files = sorted(p.name for p in output_dir.iterdir() if p.is_file())

    return {
        "construct_name": construct_name,
        "provenance": export_paths.get("provenance"),
        "sequence_length_bp": len(seq),
        "sequence_sha256": hashlib.sha256(seq.encode()).hexdigest(),
        "optimize_host": opt.get("host"),
        "optimize_gc_after": opt.get("gc_after"),
        "validate_passed": val.get("passed_checks"),
        "primer_pair_count": len(prim.get("primer_pairs") or []),
        "files": files,
    }


def manifest_json(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"
