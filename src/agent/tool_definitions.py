"""Claude tool schemas for the Crake agent.

Each entry is a dict matching the Anthropic tool format.
Import TOOL_DEFINITIONS and pass directly to client.messages.create(tools=...).
"""
from __future__ import annotations

TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "search_gene",
        "description": (
            "Search NCBI for a gene by name and source organism. "
            "Returns the DNA sequence, organism, and a suggested cloning host."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_name": {"type": "string", "description": "Gene name, e.g. 'GFP' or 'rbcL'"},
                "organism": {"type": "string", "description": "Source organism, e.g. 'Zostera marina'"},
                "full_sequence": {
                    "type": "boolean",
                    "description": "Return full genomic record instead of CDS only (for target_site use)",
                    "default": False,
                },
            },
            "required": ["gene_name", "organism"],
        },
    },
    {
        "name": "fetch_by_accession",
        "description": "Fetch a sequence from NCBI by accession number (e.g. U55762, NM_001301717).",
        "input_schema": {
            "type": "object",
            "properties": {
                "accession": {"type": "string"},
                "db": {
                    "type": "string",
                    "enum": ["nucleotide", "protein"],
                    "default": "nucleotide",
                },
                "full_sequence": {"type": "boolean", "default": False},
            },
            "required": ["accession"],
        },
    },
    {
        "name": "import_sequence",
        "description": (
            "Import a DNA sequence from a local file. "
            "Supports SnapGene (.dna), GenBank (.gb/.genbank), and FASTA (.fa/.fasta) formats. "
            "Use this when the user provides a file path to an existing plasmid or sequence."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the sequence file",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "suggest_parts",
        "description": (
            "Suggest backbone vectors, promoters, terminators, and selectable markers "
            "for a given cloning host."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "enum": ["e_coli", "plant_nuclear", "agrobacterium"],
                },
            },
            "required": ["host"],
        },
    },
    {
        "name": "optimize_codons",
        "description": (
            "Codon-optimize a coding sequence (CDS) for expression in a target host. "
            "Sequence must start with ATG and have length divisible by 3."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sequence": {"type": "string", "description": "DNA sequence to optimize"},
                "host": {
                    "type": "string",
                    "enum": ["e_coli", "plant_nuclear", "agrobacterium"],
                },
            },
            "required": ["sequence", "host"],
        },
    },
    {
        "name": "find_target_sites",
        "description": (
            "Find edit sites in a genomic sequence. "
            "restriction: single-cut enzyme sites. "
            "crispr: SpCas9 NGG PAM sites ranked by GC content. "
            "homologous: extract left/right homology arms around a position."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sequence": {"type": "string"},
                "method": {
                    "type": "string",
                    "enum": ["restriction", "crispr", "homologous"],
                },
                "position": {
                    "type": "integer",
                    "description": "Required for method=homologous",
                },
                "arm_length": {
                    "type": "integer",
                    "default": 500,
                    "description": "Homology arm length in bp",
                },
            },
            "required": ["sequence", "method"],
        },
    },
    {
        "name": "design_primers",
        "description": "Design PCR primers for a template sequence using Primer3.",
        "input_schema": {
            "type": "object",
            "properties": {
                "template": {"type": "string", "description": "Template DNA sequence"},
                "overhang_fwd": {
                    "type": "string",
                    "default": "",
                    "description": "5' overhang for forward primer (Gibson/GoldenGate)",
                },
                "overhang_rev": {
                    "type": "string",
                    "default": "",
                    "description": "5' overhang for reverse primer",
                },
                "opt_tm": {
                    "type": "number",
                    "default": 60.0,
                    "description": "Optimal melting temperature (°C)",
                },
            },
            "required": ["template"],
        },
    },
    {
        "name": "simulate_assembly",
        "description": (
            "Simulate DNA assembly from fragment sequences. "
            "gibson: overlap-based (>=20bp overlaps). "
            "restriction_ligation: digest with enzymes then ligate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fragments": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "DNA sequences or file paths to assemble",
                },
                "method": {
                    "type": "string",
                    "enum": ["gibson", "restriction_ligation"],
                },
                "enzymes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Restriction enzyme names (required for restriction_ligation)",
                },
            },
            "required": ["fragments", "method"],
        },
    },
    {
        "name": "validate_plasmid",
        "description": (
            "Validate a plasmid sequence: ORF detection, GC content analysis, "
            "restriction map, and design warnings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sequence": {"type": "string"},
                "name": {"type": "string", "default": "construct"},
            },
            "required": ["sequence"],
        },
    },
    {
        "name": "introduce_gene",
        "description": (
            "Orchestrate end-to-end gene introduction into a target host. "
            "Fetches the gene CDS from NCBI, codon-optimises it for the target host, "
            "and suggests a suitable vector backbone, promoter, terminator, and "
            "selectable marker. Returns a complete expression cassette description "
            "and next-steps protocol."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_name": {
                    "type": "string",
                    "description": "Gene to introduce, e.g. 'GFP' or 'URA3'",
                },
                "source_organism": {
                    "type": "string",
                    "description": "Source organism for the gene, e.g. 'Aequorea victoria'",
                },
                "target_host": {
                    "type": "string",
                    "enum": ["e_coli", "yeast", "plant_nuclear"],
                    "description": "Destination host organism",
                },
                "expression_goal": {
                    "type": "string",
                    "description": "Optional: brief description of the expression goal, e.g. 'fluorescence reporter'",
                    "default": "",
                },
            },
            "required": ["gene_name", "source_organism", "target_host"],
        },
    },
    {
        "name": "export_files",
        "description": (
            "Export the current design to lab-ready files: "
            "annotated GenBank (.gb), FASTA (.fa), plasmid map (.svg), "
            "primer order sheet (.csv), and wet-lab protocol (.md). "
            "Call this after validate_plasmid."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Construct name, e.g. 'pMyGene'",
                },
                "output_dir": {
                    "type": "string",
                    "default": "./crake_output",
                },
            },
            "required": ["name"],
        },
    },
]
