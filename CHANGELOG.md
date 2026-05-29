# Changelog

## [0.2.0] — 2026-05-29

### Added

- `crake hero` — offline GFP → *E. coli* demo with golden export manifest in CI
- `crake cmd` loads existing `--session-out` JSON when chaining commands
- Typed `ConstructSession` workflow state and export assembly provenance in protocols
- `/annotate` command and Annotation panel in the UI
- `crake` Typer CLI (`crake cmd`, `crake session`)
- JSON Schema validation for curated knowledge base files
- Export safety: no fake assembly on `/export`; `--allow-sequence-only` flag
- CI: ruff lint/format, pytest on Python 3.11/3.12, coverage gate on core packages
- `docs/scope.md` and Docker demo

### Changed

- Consolidated scripting on `crake` + `tool_dispatch` (removed per-tool `python src/tools/*.py` CLIs)
- README clarifies what Crake adds vs. underlying libraries; hero demo in Quick start
- Removed unused `main.py`; Docker copies `app.py` only
- Removed agent/MCP scaffolding from the public tree; Benchling remains manual file exchange

### Security

- Export bundles state whether assembly was simulated in silico

## [0.1.0] — earlier

Initial Streamlit slash-command workbench with NCBI fetch, codon optimization, parts suggestions, Gibson/restriction assembly, validation, and lab export.
