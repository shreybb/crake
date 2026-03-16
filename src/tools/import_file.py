#!/usr/bin/env python3
"""
Import a DNA sequence from a local file into the Crake session.

Supported formats:
    .dna        SnapGene native format (via snapgene-reader)
    .gb / .genbank  Annotated GenBank flat file (via Biopython)
    .fa / .fasta    Plain FASTA (via Biopython)

Usage:
    python src/tools/import_file.py --path /path/to/plasmid.gb
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from Bio import SeqIO
from Bio.SeqRecord import SeqRecord

from .fetch_sequence import infer_host


def _seqrecord_to_result(record: SeqRecord, source_path: str) -> dict:
    """Convert a Biopython SeqRecord to the standard Crake result dict."""
    sequence = str(record.seq).upper()
    organism = record.annotations.get("organism", "unknown")
    topology = record.annotations.get("topology", "linear")

    features = []
    for feat in record.features:
        if feat.type == "source":
            continue
        name = (
            feat.qualifiers.get("gene", feat.qualifiers.get("note", [feat.type]))[0]
            if feat.qualifiers
            else feat.type
        )
        features.append({
            "name": name,
            "type": feat.type,
            "start": int(feat.location.start),
            "end": int(feat.location.end),
            "strand": feat.location.strand if feat.location.strand is not None else 1,
        })

    return {
        "accession": record.id or Path(source_path).stem,
        "gene_name": record.name or Path(source_path).stem,
        "organism": organism,
        "sequence": sequence,
        "length_bp": len(sequence),
        "sequence_type": "genomic",
        "description": record.description,
        "topology": topology,
        "features": features,
        "db": "local_file",
        "source_path": source_path,
        "suggested_host": infer_host(organism),
    }


def import_sequence(path: str) -> dict:
    """Load a DNA sequence from a local file.

    Dispatches to the correct parser based on file extension.
    Returns the same dict shape as ``fetch_by_accession``.
    """
    p = Path(path)
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if not p.is_file():
        return {"error": f"Not a file: {path}"}

    suffix = p.suffix.lower()

    try:
        if suffix == ".dna":
            return _import_snapgene(p)
        if suffix in (".gb", ".genbank"):
            return _import_genbank(p)
        if suffix in (".fa", ".fasta"):
            return _import_fasta(p)
        return {"error": f"Unsupported file type '{suffix}'. Use .dna, .gb, .genbank, .fa, or .fasta"}
    except Exception as exc:
        return {"error": str(exc), "path": path}


def _import_snapgene(path: Path) -> dict:
    from snapgene_reader import snapgene_file_to_seqrecord
    record = snapgene_file_to_seqrecord(str(path))
    return _seqrecord_to_result(record, str(path))


def _import_genbank(path: Path) -> dict:
    record = SeqIO.read(str(path), "genbank")
    return _seqrecord_to_result(record, str(path))


def _import_fasta(path: Path) -> dict:
    record = SeqIO.read(str(path), "fasta")
    return _seqrecord_to_result(record, str(path))


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a sequence file into Crake")
    parser.add_argument("--path", required=True, help="Path to .dna, .gb, .genbank, .fa, or .fasta file")
    args = parser.parse_args()
    print(json.dumps(import_sequence(args.path), indent=2))


if __name__ == "__main__":
    main()
