# Crake

[![Tests](https://github.com/shreybb/crake/actions/workflows/test.yml/badge.svg)](https://github.com/shreybb/crake/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **TL;DR** — A **deterministic cloning assistant** for four hosts: fetch a CDS, codon-optimize, validate, design primers, simulate Gibson assembly, and export GenBank + primers + protocol. **No LLM in the hot path.** Streamlit UI or `crake` CLI — same Python dispatch layer underneath.

**Scope:** [docs/scope.md](docs/scope.md) — what v1 includes and explicitly does not ship.

---

## What it is

Cloning design is a lot of tab-hopping: NCBI for the CDS, spreadsheets for parts, SnapGene for maps, another sheet for primers. **Crake** chains those steps with slash commands. Every step is a library call (Entrez, DnaChisel, Primer3, pydna, BioPython). Same input → same output.

Crake is **not** a production LIMS, parts registry, or AI design platform. The knowledge base is curated starter data for supported hosts, validated in CI.

### Limitations (honest)

| Topic | v1 behavior |
|-------|-------------|
| Hosts | `e_coli`, `yeast`, `plant_nuclear`, `agrobacterium` only |
| Gibson | Two fragments per simulation |
| Export without `/assemble` | Requires `/export <name> --allow-sequence-only`; protocol warns |
| Golden Gate / Benchling | Out of scope — see [roadmap](docs/roadmap.md) |

---

## Quick start

```bash
git clone https://github.com/shreybb/crake.git
cd crake
uv sync
cp .env.example .env   # NCBI_EMAIL required for live fetch
uv run streamlit run app.py
```

CLI (same commands):

```bash
uv run crake cmd "/help"
uv run crake cmd "/load ./plasmid.gb"
```

Docker demo:

```bash
docker compose up --build
```

---

## Typical workflow

```
/genesearch GFP in Aequorea victoria
/optimize yeast
/validate
/annotate
/primers
/assemble gibson backbone.fa
/export pMyGFP
```

Outputs: `./crake_output/` — GenBank, FASTA, SVG map, primer CSV, protocol with **assembly provenance**.

---

## Commands

| Command | What it does |
|---------|--------------|
| `/genesearch`, `/fetch`, `/load` | Load sequence |
| `/suggest`, `/optimize` | Parts + codon optimization |
| `/targets`, `/annotate` | Edit sites + restriction map |
| `/primers`, `/assemble` | Primers + Gibson / restriction-ligation sim |
| `/validate`, `/export` | Checks + lab bundle |
| `/introduce-gene` | End-to-end pipeline (sidebar form too) |

Full list: `/help` or [docs/cli.md](docs/cli.md).

---

## Tests

```bash
uv run pytest
uv run ruff check .
```

Unit and integration tests mock NCBI in CI. Export provenance is covered in protocol output.

---

## Project structure

```
crake/
├── app.py                 # Streamlit UI
├── src/
│   ├── agent/             # Slash commands → dispatch
│   ├── session/           # ConstructSession workflow state
│   ├── tools/             # Bioinformatics
│   └── knowledge/         # Curated JSON + schemas
├── docs/scope.md          # Product boundary
└── tests/
```

---

## Docs

- [Scope](docs/scope.md) — v1 boundary
- [Architecture](docs/architecture.md) — session model and dispatch
- [CLI](docs/cli.md) — `crake` and tool scripts
- [Roadmap](docs/roadmap.md)
- [Contributing](CONTRIBUTING.md)

---

## License

MIT
