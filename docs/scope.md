# Crake v1 scope

Crake is a **deterministic cloning assistant** for four expression hosts. It orchestrates established bioinformatics libraries (BioPython, DnaChisel, Primer3, pydna) and a **curated starter parts knowledge base** — not a full LIMS, parts registry, or AI design platform.

## In scope (v1)

| Area | What ships |
|------|------------|
| Hosts | `e_coli`, `yeast`, `plant_nuclear`, `agrobacterium` |
| Interfaces | Streamlit slash-command UI (primary); Typer CLI `crake` (same dispatch layer) |
| Sequence I/O | NCBI gene search, accession fetch, UniProt protein fetch, local `.gb` / `.fa` / `.dna` import |
| Design | Codon optimization, curated part suggestions, CRISPR/restriction/homology targets, PCR primers |
| Assembly simulation | Gibson (2 fragments), restriction–ligation |
| Validation | ORFs, GC windows, restriction map, warnings |
| Annotation | Restriction site scan via `/annotate` |
| Export | GenBank, FASTA, SVG map, primer CSV, protocol with **assembly provenance** |
| Session | Typed `ConstructSession` workflow state (sequence → optimize → validate → assemble → export) |

## Out of scope (v1 non-goals)

| Area | Status |
|------|--------|
| Golden Gate assembly | Deferred — protocol stub only in export |
| Benchling / LIMS sync | Manual import/export only (GenBank/FASTA) |
| In-app LLM chat | Not planned — slash commands and `crake` CLI call `tool_dispatch` directly |
| Multi-user deployment / auth | Single-user local or demo Docker only |
| Broad organism support | Unsupported hosts get a warning and closest-host fallback |

## Knowledge base

Files under `src/knowledge/*.json` are **curated starter parts** for supported hosts. They are validated against JSON Schema in CI. They are not a scalable, community-maintained parts registry.

## Export safety

Export never fabricates a successful in-silico assembly. If assembly was not simulated, the protocol states **sequence-only export** and warns the user to verify before ordering.

## Versioning

v1 ships as **0.2.x** (Alpha). See [roadmap.md](roadmap.md) for implemented vs planned items.
