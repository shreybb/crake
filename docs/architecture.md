# Architecture

Crake is a **deterministic** plasmid design workbench: every user action runs fixed Python tools. There is no LLM in the request path.

## Layers

```
Streamlit UI (app.py)
    │
    ├─ Sidebar: Introduce a Gene form
    └─ Chat input: slash commands
            │
            ▼
    command_runner.py  — parse args, build tool input dicts
            │
            ▼
    tool_dispatch.py   — route tool name → src/tools/*, update session
            │
            ▼
    src/tools/*        — BioPython, DnaChisel, Primer3, pydna, NCBI Entrez
            │
            ▼
    knowledge/*.json   — curated promoters, backbones, terminators, markers
```

## Session state

`tool_dispatch.dispatch` writes into Streamlit `session_state`:

| Key | Set by |
|-----|--------|
| `last_sequence` | fetch, import, search, introduce_gene, assembly |
| `last_optimization` | optimize_codons, introduce_gene |
| `last_validation` | validate_plasmid |
| `last_primers` | design_primers |
| `last_assembly` | simulate_assembly |
| `last_seqviz` | sequence viewer payload |
| `export_paths` | export_files |

Downstream commands (e.g. `/optimize`, `/validate`, `/export`) read `last_sequence` unless a command supplies its own sequence.

## Tool schemas

`src/agent/tool_definitions.py` lists `TOOL_DEFINITIONS` — parameter shapes used by tests to stay aligned with `tool_dispatch` handlers. Slash commands in `commands.py` are the user-facing subset.

## Tests

Unit tests mock NCBI and heavy dependencies. Run with:

```bash
uv run pytest
```

UI code under `src/ui/` is omitted from coverage config but exercised indirectly via command/dispatch tests.
