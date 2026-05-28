# Command-line tools

Each bioinformatics capability lives under `src/tools/` and can be run as a standalone script. Examples are in `main.py`.

General pattern:

```bash
uv run python src/tools/<module>.py --help
```

## Modules

| Script | Purpose |
|--------|---------|
| `fetch_sequence.py` | NCBI gene search, accession fetch, UniProt protein |
| `import_file.py` | SnapGene `.dna`, GenBank, FASTA import |
| `sequence_design.py` | Codon optimization, part suggestions |
| `target_site.py` | CRISPR PAM, restriction sites, homology arms |
| `primer_design.py` | Primer3 PCR primers |
| `assembly.py` | Gibson or restriction–ligation simulation |
| `validation.py` | ORFs, GC, restriction map, warnings |
| `gene_introduction.py` | End-to-end fetch → optimize → suggest parts |
| `export.py` | GenBank, FASTA, SVG map, primer CSV, protocol |
| `annotation.py` | Restriction sites; GenBank feature summary |

## Environment

Set `NCBI_EMAIL` (and optionally `NCBI_API_KEY`) before using `fetch_sequence.py` or any command that hits Entrez. See `.env.example`.

## Streamlit vs CLI

The Streamlit app (`app.py`) does not shell out to these scripts; it calls the same functions through `tool_dispatch.py`. Behavior should match between UI slash commands and direct script use.
