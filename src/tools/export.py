#!/usr/bin/env python3
"""
Export pipeline artifacts to files ready for wet-lab use.

Usage:
    python src/tools/export.py \
        --assembly assembly.json \
        --validation validation.json \
        --primers primers.json \
        --name pMyConstruct \
        --output-dir ./output/

Produces in --output-dir:
    <name>.gb          Annotated GenBank (opens in SnapGene, ApE, Benchling, etc.)
    <name>.fa          FASTA sequence
    <name>_map.svg     Circular/linear plasmid map
    primers.csv        IDT / Eurofins bulk-order CSV
    protocol.md        Wet-lab instruction sheet
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import SeqFeature, SimpleLocation
from Bio.SeqRecord import SeqRecord


# ---------------------------------------------------------------------------
# GenBank export
# ---------------------------------------------------------------------------

def write_genbank(
    assembly_json: dict,
    validation_json: dict,
    name: str,
    output_path: Path,
) -> Path:
    """Write an annotated GenBank file from assembly + validation JSON.

    ORFs found during validation are added as CDS features.
    Restriction sites are added as misc_binding features.

    Returns the path written.
    """
    sequence = assembly_json.get("product_sequence", "")
    topology = assembly_json.get("topology", "circular")

    record = SeqRecord(
        Seq(sequence),
        id=name,
        name=name[:16],  # GenBank name field is limited to 16 chars
        description=f"Designed by Crake on {date.today().isoformat()}",
        annotations={
            "molecule_type": "DNA",
            "topology": topology,
        },
    )

    for orf in validation_json.get("orfs", []):
        strand = orf.get("strand", 1)
        feat = SeqFeature(
            SimpleLocation(orf["start_nt"], orf["end_nt"], strand=strand),
            type="CDS",
            qualifiers={"note": [f"ORF {orf['length_aa']} aa"]},
        )
        record.features.append(feat)

    for site in validation_json.get("restriction_sites", []):
        for pos in site.get("positions", []):
            feat = SeqFeature(
                SimpleLocation(pos, pos + 6, strand=0),
                type="misc_binding",
                qualifiers={"note": [site["enzyme"]]},
            )
            record.features.append(feat)

    out = Path(output_path)
    SeqIO.write(record, str(out), "genbank")
    return out


# ---------------------------------------------------------------------------
# FASTA export
# ---------------------------------------------------------------------------

def write_fasta(sequence: str, name: str, output_path: Path) -> Path:
    """Write a single-entry FASTA file."""
    record = SeqRecord(Seq(sequence), id=name, description="")
    out = Path(output_path)
    SeqIO.write(record, str(out), "fasta")
    return out


# ---------------------------------------------------------------------------
# Primers CSV (IDT bulk order format)
# ---------------------------------------------------------------------------

_IDT_COLUMNS = ("Name", "Sequence", "Scale", "Purification")
_DEFAULT_SCALE = "25nm"
_DEFAULT_PURIFICATION = "STD"


def write_primers_csv(primer_pairs: list[dict], output_path: Path) -> Path:
    """Write an IDT / Eurofins compatible primer order CSV.

    Accepts the ``primer_pairs`` list from ``primer_design.py`` JSON output.
    """
    out = Path(output_path)
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(_IDT_COLUMNS))
        writer.writeheader()
        for i, pair in enumerate(primer_pairs):
            rank = pair.get("rank", i)
            for direction in ("forward", "reverse"):
                p = pair.get(direction, {})
                seq = p.get("full_sequence") or p.get("binding_region", "")
                if not seq:
                    continue
                abbrev = "FWD" if direction == "forward" else "REV"
                writer.writerow({
                    "Name": f"Primer_{rank + 1}_{abbrev}",
                    "Sequence": seq,
                    "Scale": _DEFAULT_SCALE,
                    "Purification": _DEFAULT_PURIFICATION,
                })
    return out


# ---------------------------------------------------------------------------
# Protocol Markdown
# ---------------------------------------------------------------------------

def write_protocol_md(
    assembly_json: dict,
    primer_json: dict,
    validation_json: dict,
    name: str,
    output_path: Path,
) -> Path:
    """Generate a Markdown wet-lab protocol from pipeline JSON outputs."""
    method = assembly_json.get("method", "unknown")
    topology = assembly_json.get("topology", "circular")
    length = assembly_json.get("product_length_bp", "?")
    parts = assembly_json.get("input_parts", [])
    warnings = validation_json.get("warnings", [])
    gc = validation_json.get("gc_analysis", {}).get("overall_gc_percent", "?")
    pairs = primer_json.get("primer_pairs", [])

    lines: list[str] = [
        f"# Cloning Protocol: {name}",
        f"_Generated {date.today().isoformat()} by Crake_",
        "",
        "## Construct Summary",
        f"- **Method**: {method.replace('_', ' ').title()}",
        f"- **Topology**: {topology}",
        f"- **Expected size**: {length} bp",
        f"- **GC content**: {gc}%",
        "",
        "## Input Parts",
    ]

    for part in parts:
        lines.append(f"- {part.get('name', 'unnamed')} ({part.get('length', '?')} bp)")

    lines += ["", "## Primers"]
    if pairs:
        lines.append(
            "| # | Direction | Sequence | Tm (°C) | GC% | Length |"
        )
        lines.append("|---|-----------|----------|---------|-----|--------|")
        for pair in pairs:
            rank = pair.get("rank", 0) + 1
            for direction in ("forward", "reverse"):
                p = pair.get(direction, {})
                seq = p.get("full_sequence") or p.get("binding_region", "—")
                tm = p.get("tm_celsius", "—")
                gc_p = p.get("gc_percent", "—")
                length_p = p.get("length", "—")
                lines.append(
                    f"| {rank} | {direction.capitalize()} | `{seq}` | {tm} | {gc_p} | {length_p} |"
                )
    else:
        lines.append("_No primer data provided._")

    lines += ["", "## Restriction Sites (for verification digest)"]
    rsites = validation_json.get("restriction_sites", [])
    if rsites:
        lines.append("| Enzyme | Positions | Count |")
        lines.append("|--------|-----------|-------|")
        for site in rsites[:15]:
            lines.append(
                f"| {site['enzyme']} | {site['positions']} | {site['count']} |"
            )
    else:
        lines.append("_No restriction site data provided._")

    if warnings:
        lines += ["", "## Warnings", ""]
        for w in warnings:
            lines.append(f"- ⚠️  {w}")

    lines += [
        "",
        "## Assembly Steps",
        "",
        _protocol_steps(method),
        "",
        "---",
        "_Review the annotated GenBank file and plasmid map before ordering._",
    ]

    out = Path(output_path)
    out.write_text("\n".join(lines))
    return out


def _protocol_steps(method: str) -> str:
    steps = {
        "gibson": (
            "1. PCR-amplify each fragment with primers above (check Tm, use Q5/Phusion).\n"
            "2. DpnI-treat PCR products if template is plasmid DNA.\n"
            "3. Gel-purify or column-purify each fragment.\n"
            "4. Combine equimolar amounts (~50–100 ng each) in 5 µL.\n"
            "5. Add 15 µL Gibson Assembly Master Mix (NEB #E2611).\n"
            "6. Incubate 50 °C × 60 min.\n"
            "7. Transform 2 µL into 25 µL competent cells (DH5α or Stbl3).\n"
            "8. Plate on selective media; pick 4–8 colonies.\n"
            "9. Verify by colony PCR and Sanger sequencing."
        ),
        "restriction_ligation": (
            "1. Digest insert and backbone with listed enzymes (37 °C × 1 h).\n"
            "2. Run on gel; excise correct bands.\n"
            "3. Gel-purify insert and linearised backbone.\n"
            "4. Ligate at 16 °C × 1 h (T4 DNA Ligase, NEB #M0202) or RT × 5 min (Quick Ligase).\n"
            "5. Transform 2 µL into 25 µL competent cells.\n"
            "6. Plate on selective media; pick 4–8 colonies.\n"
            "7. Verify by colony PCR and Sanger sequencing."
        ),
        "golden_gate": (
            "1. Combine all parts and Golden Gate enzyme mix in one tube.\n"
            "2. Cycle: 37 °C × 2 min / 16 °C × 3 min, ×25 cycles; then 60 °C × 5 min.\n"
            "3. Transform 2 µL into 25 µL competent cells.\n"
            "4. Plate on selective media; pick 4–8 colonies.\n"
            "5. Verify by colony PCR and Sanger sequencing."
        ),
    }
    return steps.get(method, f"_Protocol for method '{method}' — refer to manufacturer instructions._")


# ---------------------------------------------------------------------------
# Plasmid map (SVG)
# ---------------------------------------------------------------------------

def write_plasmid_map(genbank_path: Path, output_path: Path) -> Path:
    """Render an annotated plasmid map as SVG using dna-features-viewer.

    BiopythonTranslator auto-detects the topology annotation and returns
    a CircularGraphicRecord for circular sequences and a GraphicRecord for
    linear ones — both render correctly with plain .plot().
    """
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend for headless server use
    import matplotlib.pyplot as plt
    from dna_features_viewer import BiopythonTranslator

    record = SeqIO.read(str(genbank_path), "genbank")
    translator = BiopythonTranslator()
    graphic_record = translator.translate_record(record)

    ax, _ = graphic_record.plot(figure_width=8)
    ax.figure.savefig(str(output_path), format="svg", bbox_inches="tight")
    plt.close("all")

    return Path(output_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_json(path: str | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        print(f"Warning: {path} not found — skipping", file=sys.stderr)
        return {}
    return json.loads(p.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Crake pipeline outputs to lab-ready files"
    )
    parser.add_argument("--assembly", help="Path to assembly.json")
    parser.add_argument("--validation", help="Path to validation.json")
    parser.add_argument("--primers", help="Path to primers.json")
    parser.add_argument("--name", required=True, help="Construct name (e.g. pMyGene)")
    parser.add_argument(
        "--output-dir", required=True, help="Directory to write output files"
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    assembly = _load_json(args.assembly)
    validation = _load_json(args.validation)
    primers = _load_json(args.primers)

    results: dict[str, str] = {}

    sequence = assembly.get("product_sequence", "")

    if sequence and assembly:
        gb_path = out_dir / f"{args.name}.gb"
        write_genbank(assembly, validation, args.name, gb_path)
        results["genbank"] = str(gb_path)

        fa_path = out_dir / f"{args.name}.fa"
        write_fasta(sequence, args.name, fa_path)
        results["fasta"] = str(fa_path)

        try:
            svg_path = out_dir / f"{args.name}_map.svg"
            write_plasmid_map(gb_path, svg_path)
            results["map"] = str(svg_path)
        except Exception as exc:
            results["map_error"] = str(exc)

    primer_pairs = primers.get("primer_pairs", [])
    if primer_pairs:
        csv_path = out_dir / "primers.csv"
        write_primers_csv(primer_pairs, csv_path)
        results["primers_csv"] = str(csv_path)

    if assembly or validation or primers:
        md_path = out_dir / "protocol.md"
        write_protocol_md(assembly, primers, validation, args.name, md_path)
        results["protocol"] = str(md_path)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
