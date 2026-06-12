#!/usr/bin/env python3
"""
Fetch gene sequences from NCBI GenBank or UniProt.

CLI: ``crake cmd "/genesearch GFP in Aequorea victoria"`` or ``/fetch U55762``.
"""

from __future__ import annotations

import os
import time
import urllib.request

from Bio import Entrez, SeqIO
from Bio.SeqRecord import SeqRecord
from dotenv import load_dotenv

load_dotenv()

_INVALID_NCBI_EMAILS = frozenset({"", "crake@localhost", "you@example.com"})

_NCBI_API_KEY = os.environ.get("NCBI_API_KEY")
if _NCBI_API_KEY:
    Entrez.api_key = _NCBI_API_KEY

# 3 req/s without API key; 10 req/s with one
_NCBI_DELAY = 0.1 if _NCBI_API_KEY else 0.34

_NCBI_EMAIL_HELP = (
    "NCBI_EMAIL is required for NCBI gene search and accession fetch. "
    "Copy .env.example to .env and set NCBI_EMAIL to a valid contact address "
    "(see https://www.ncbi.nlm.nih.gov/home/about/policies/)."
)


def ncbi_email_error() -> str | None:
    """Return an error message if NCBI_EMAIL is missing or a placeholder."""
    email = os.environ.get("NCBI_EMAIL", "").strip()
    if email.lower() in _INVALID_NCBI_EMAILS or "@" not in email:
        return _NCBI_EMAIL_HELP
    return None


def _apply_ncbi_email() -> None:
    """Configure Entrez.email from NCBI_EMAIL (call after :func:`ncbi_email_error` is clear)."""
    Entrez.email = os.environ.get("NCBI_EMAIL", "").strip()


_PLANT_KEYWORDS = {
    "arabidopsis",
    "thaliana",
    "tobacco",
    "nicotiana",
    "rice",
    "oryza",
    "maize",
    "zea",
    "tomato",
    "solanum",
    "soybean",
    "glycine",
    "wheat",
    "triticum",
    "potato",
    "cotton",
    "gossypium",
    "brassica",
    "poplar",
    "populus",
    "agrobacterium",
    "tumefaciens",
    "rhizobiaceae",
}

_YEAST_KEYWORDS = {
    "saccharomyces",
    "cerevisiae",
    "yeast",
    "schizosaccharomyces",
    "pombe",
    "pichia",
    "pastoris",
    "kluyveromyces",
    "yarrowia",
    "candida",
}


def infer_host(organism: str) -> str:
    """Map source organism to the recommended cloning host.

    Plant-derived or Agrobacterium genes → agrobacterium (binary vector + T-DNA).
    Yeast-derived genes → yeast (S. cerevisiae expression system).
    Everything else defaults to e_coli.
    """
    lower = organism.lower()
    if any(kw in lower for kw in _PLANT_KEYWORDS):
        return "agrobacterium"
    if any(kw in lower for kw in _YEAST_KEYWORDS):
        return "yeast"
    return "e_coli"


def _topology_from_record(record: SeqRecord) -> str:
    """Normalize GenBank topology annotation to ``circular`` or ``linear``."""
    raw = str(record.annotations.get("topology", "linear")).lower()
    return "circular" if raw == "circular" else "linear"


def _extract_cds(record: SeqRecord) -> tuple[str, str]:
    """Return (sequence, seq_type) from a GenBank record.

    Prefers the first CDS feature so downstream codon optimisation works
    on a clean coding sequence.  Falls back to the full record sequence.
    """
    for feat in record.features:
        if feat.type == "CDS":
            return str(feat.extract(record.seq)).upper(), "CDS"
    return str(record.seq).upper(), "genomic"


def fetch_by_accession(
    accession: str,
    db: str = "nucleotide",
    full_sequence: bool = False,
) -> dict:
    """Fetch a sequence record from NCBI by accession number.

    Args:
        accession: NCBI accession (e.g. ``U55762``, ``NP_000483``).
        db: NCBI database — ``nucleotide`` or ``protein``.
        full_sequence: When True, return the full genomic sequence instead of
            only the first CDS (useful as input for ``target_site``).

    Returns:
        JSON-serialisable dict with ``sequence``, ``suggested_host`` and metadata.
    """
    if err := ncbi_email_error():
        return {"error": err, "accession": accession}
    _apply_ncbi_email()
    try:
        fmt = "gb" if db == "nucleotide" else "fasta"
        handle = Entrez.efetch(db=db, id=accession, rettype=fmt, retmode="text")
        parse_fmt = "genbank" if db == "nucleotide" else "fasta"
        record = SeqIO.read(handle, parse_fmt)
        handle.close()

        topology = "linear"
        if db == "nucleotide":
            if full_sequence:
                sequence, seq_type = str(record.seq).upper(), "genomic"
            else:
                sequence, seq_type = _extract_cds(record)
            organism = record.annotations.get("organism", "unknown")
            topology = _topology_from_record(record)
        else:
            sequence, seq_type = str(record.seq).upper(), "protein"
            organism = "unknown"

        result = {
            "accession": record.id,
            "gene_name": record.name,
            "organism": organism,
            "sequence": sequence,
            "length_bp": len(sequence),
            "sequence_type": seq_type,
            "description": record.description,
            "db": f"ncbi_{db}",
            "suggested_host": infer_host(organism),
        }
        if db == "nucleotide":
            result["topology"] = topology
        return result
    except Exception as exc:
        return {"error": str(exc), "accession": accession}


def search_gene(gene_name: str, organism: str, full_sequence: bool = False) -> dict:
    """Search NCBI nucleotide for a gene by name and organism.

    Runs a precise ``[Gene Name] AND [Organism] AND CDS`` query first,
    then falls back to a free-text search if nothing is found.

    Returns the top hit fetched via :func:`fetch_by_accession`.
    """
    if err := ncbi_email_error():
        return {"error": err, "gene": gene_name, "organism": organism}
    _apply_ncbi_email()
    precise = f'"{gene_name}"[Gene Name] AND "{organism}"[Organism] AND CDS[Feature Key]'
    broad = f"{gene_name}[All Fields] AND {organism}[Organism]"

    for query in (precise, broad):
        try:
            handle = Entrez.esearch(db="nucleotide", term=query, retmax=1)
            results = Entrez.read(handle)
            handle.close()
            ids = results.get("IdList", [])
            if ids:
                time.sleep(_NCBI_DELAY)
                result = fetch_by_accession(ids[0], full_sequence=full_sequence)
                result.setdefault("gene_name", gene_name)
                result["search_query"] = {"gene": gene_name, "organism": organism}
                return result
        except Exception as exc:
            return {"error": str(exc), "gene": gene_name, "organism": organism}

    return {
        "error": f"No results for gene '{gene_name}' in organism '{organism}'",
        "gene": gene_name,
        "organism": organism,
    }


def fetch_from_uniprot(uniprot_id: str) -> dict:
    """Fetch a protein sequence from UniProt REST API.

    Returns ``sequence_type: protein`` — pass the result through
    ``sequence_design --optimize-codons`` after back-translating.
    """
    url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.fasta"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            fasta_text = resp.read().decode("utf-8")

        lines = fasta_text.strip().split("\n")
        header = lines[0]
        protein_seq = "".join(lines[1:])

        organism = "unknown"
        if "OS=" in header:
            os_part = header.split("OS=")[1]
            organism = os_part.split(" OX=")[0].strip()

        return {
            "accession": uniprot_id,
            "gene_name": uniprot_id,
            "organism": organism,
            "sequence": protein_seq,
            "length_aa": len(protein_seq),
            "sequence_type": "protein",
            "description": header.lstrip(">"),
            "db": "uniprot",
            "suggested_host": infer_host(organism),
            "note": (
                "Protein sequence — back-translate then run "
                "sequence_design --optimize-codons for host-specific DNA optimisation"
            ),
        }
    except Exception as exc:
        return {"error": str(exc), "uniprot_id": uniprot_id}
