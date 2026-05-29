# Roadmap

Current scope: **deterministic** workflows for bacterial, yeast, and plant/Agrobacterium-oriented cloning.

## Implemented

- Slash-command Streamlit UI and Introduce a Gene pipeline
- NCBI fetch (with GenBank `topology` on nucleotide records), codon optimization, curated parts knowledge base
- Session chain: `/optimize` updates `last_sequence`; failed Gibson does not overwrite `last_assembly`; introduce-gene sets vector, topology, and seqviz
- `.env` auto-load via `python-dotenv` in the Streamlit app and fetch tools
- CRISPR/restriction/homology target finding (configurable PAM, including `/targets crispr TTTV`)
- NCBI email validation before Entrez requests
- Primer design, Gibson and restriction–ligation assembly simulation
- Validation and lab export (GenBank, FASTA, SVG, CSV, protocol)
- Integration test for import → optimize → validate → primers → assemble → export (`tests/integration/test_workflow_chain.py`)

## Planned / not yet built

| Area | Notes |
|------|--------|
| Golden Gate assembly | No simulator in `assembly.py` (export protocol stub only) |
| `/annotate` slash command | `annotation.py` is CLI-only today |
| Benchling integration | Optional MCP example only; no in-app sync |
| Additional hosts | Many organisms are intentionally unsupported or approximated |

## Non-goals (for this repo)

- In-app LLM chat (use slash commands or external agents calling `tool_dispatch`)
- Internal multi-agent orchestration (removed from public tree)

Contributions welcome for items in the planned section — see [CONTRIBUTING.md](../CONTRIBUTING.md).
