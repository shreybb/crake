# Roadmap

See [scope.md](scope.md) for the v1 product boundary.

## Implemented (v0.2)

- Slash-command Streamlit UI and Introduce a Gene pipeline
- Typer CLI (`crake cmd`, `crake session`)
- Typed `ConstructSession` workflow state with export provenance
- NCBI fetch, codon optimization, curated parts (JSON Schema validated)
- `/annotate` restriction map
- CRISPR / restriction / homology targets
- Primer design, Gibson and restriction–ligation assembly simulation
- Validation and lab export (GenBank, FASTA, SVG, CSV, protocol)
- Integration test: import → optimize → validate → primers → assemble → export
- CI: pytest matrix, ruff, coverage gate on core packages
- Optional Docker demo

## Deferred (not v1)

| Area | Notes |
|------|--------|
| Golden Gate assembly | No simulator; protocol stub only |
| Benchling integration | Optional MCP — [integrations/benchling-mcp.md](integrations/benchling-mcp.md) |
| Additional hosts | Unsupported organisms warn and approximate |

## Non-goals

- In-app LLM chat
- Internal multi-agent orchestration
- Multi-user / auth / LIMS deployment

Contributions welcome for deferred items — see [CONTRIBUTING.md](../CONTRIBUTING.md).
