# Roadmap

Current scope: **deterministic** workflows for bacterial, yeast, and plant/Agrobacterium-oriented cloning.

## Implemented

- Slash-command Streamlit UI and Introduce a Gene pipeline
- NCBI fetch, codon optimization, curated parts knowledge base
- CRISPR/restriction/homology target finding (configurable PAM, including `/targets crispr TTTV`)
- NCBI email validation before Entrez requests
- Primer design, Gibson and restriction–ligation assembly simulation
- Validation and lab export (GenBank, FASTA, SVG, CSV, protocol)

## Planned / not yet built

| Area | Notes |
|------|--------|
| Golden Gate assembly | Listed in domain types; no simulator in `assembly.py` |
| `/annotate` slash command | `annotation.py` is CLI-only today |
| Domain model wiring | `src/domain/` types are tested but not used in the live pipeline |
| Benchling integration | Optional MCP example only; no in-app sync |
| Additional hosts | Many organisms are intentionally unsupported or approximated |

## Non-goals (for this repo)

- In-app LLM chat (use slash commands or external agents calling `tool_dispatch`)
- Internal multi-agent orchestration (removed from public tree)

Contributions welcome for items in the planned section — see [CONTRIBUTING.md](../CONTRIBUTING.md).
