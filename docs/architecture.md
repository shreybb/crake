# Architecture

Crake is a **deterministic** plasmid design workbench: every user action runs fixed Python tools. There is no LLM in the request path.

## Clients

| Client | Entry | Session backing |
|--------|-------|-----------------|
| Streamlit | `app.py` | `st.session_state` ↔ `ConstructSession` via adapter |
| Typer CLI | `src/cli.py` | Ephemeral dict or JSON session file |

Both call `command_runner.execute_command` → `tool_dispatch.dispatch`.

## Layers

```
Streamlit / crake CLI
        │
        ▼
command_runner.py  — parse slash args
        │
        ▼
tool_dispatch.py — route tool → src/tools/*
        │
        ▼
ConstructSession   — sequence, assembly, validation, primers, export_paths
        │
        ▼
src/tools/*        — BioPython, DnaChisel, Primer3, pydna, Entrez
src/knowledge/*    — curated JSON (schema-validated)
```

## ConstructSession

Defined in `src/session/construct.py`:

| Field | Purpose |
|-------|---------|
| `sequence` | Active `LoadedSequence` |
| `optimization` | Last codon optimization result |
| `assembly` | `AssemblyRecord` with `provenance`: `simulated` or `not_run` |
| `validation`, `primers`, `annotation` | Tool outputs |
| `export_paths` | Last export file paths |

Key methods:

- `promote_optimized()` — single path after `/optimize`
- `record_assembly()` — only on successful simulation
- `export_readiness()` — warnings before export
- `assembly_for_export(allow_sequence_only)` — never fabricates Gibson success

## Export safety

`/export` without a simulated assembly raises an error unless `--allow-sequence-only` is passed. The generated `protocol.md` includes a **Provenance** section stating whether assembly was simulated.

## Tool schemas

`src/agent/tool_definitions.py` lists parameters for each dispatch tool. Tests keep schemas aligned with handlers.

## Tests

```bash
uv run pytest
```

NCBI is mocked in CI. UI code under `src/ui/` is omitted from coverage targets; session adapter is tested directly.
