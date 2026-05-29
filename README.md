# Crake

[![Tests](https://github.com/shreybb/crake/actions/workflows/test.yml/badge.svg)](https://github.com/shreybb/crake/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **In one sentence** — Crake is a **step-by-step lab prep tool** that helps you take a gene you found online, tune it for the organism you want to grow it in, check that the DNA looks sane, plan PCR primers, simulate how pieces snap together, and export files your bench team can actually use. Same inputs always give the same outputs; no AI guessing in the middle.

**Product boundary:** [docs/scope.md](docs/scope.md) — what v1 includes and what it deliberately does not.

---

## What Crake adds (vs. the tools it uses)

Crake does **not** replace NCBI, SnapGene, or Benchling. It **orchestrates** them into one deterministic pipeline:

| Crake layer | What it does |
|-------------|----------------|
| **Workflow state** | `ConstructSession` tracks sequence → optimization → validation → assembly → export |
| **Slash commands + CLI** | Same steps in Streamlit or `crake cmd` / `crake hero` |
| **Curated parts** | Starter promoters, backbones, markers (JSON, schema-validated) |
| **Lab export** | GenBank, FASTA, SVG map, primer CSV, protocol — with **assembly provenance** (never fakes a simulated Gibson run) |

Under the hood it calls **BioPython**, **DnaChisel**, **Primer3**, **pydna**, and **NCBI Entrez** (when you fetch genes). Crake’s value is glue, guardrails, and repeatable exports — not new aligners or codon algorithms.

**Supported hosts (v1):** *E. coli*, yeast, plant nucleus, *Agrobacterium*.

**Interfaces:** Streamlit app (primary) or `crake` CLI — both use the same dispatch layer.

### Honest limits

| Topic | v1 behavior |
|-------|-------------|
| Hosts | Only the four listed above |
| Gibson simulation | Two fragments at a time |
| Export without assembly step | Allowed only with an explicit flag; the protocol warns you |
| Golden Gate, Benchling sync | Not in v1 — see [roadmap](docs/roadmap.md) |

---

## Quick start

**Try it in ~30 seconds (no browser, no NCBI):**

```bash
git clone https://github.com/shreybb/crake.git
cd crake
uv sync
uv run crake hero
```

Output: `./crake_output/hero_demo/` — GFP codon-optimized for *E. coli*, primers, GenBank, FASTA, plasmid map, and protocol. Same command runs in CI against a golden manifest.

**Full UI** (needs `NCBI_EMAIL` in `.env` for live gene lookup):

```bash
cp .env.example .env   # set NCBI_EMAIL
uv run streamlit run app.py
```

Example session in the chat box:

```
/genesearch GFP in Aequorea victoria
/optimize yeast
/validate
/annotate
/primers
/assemble gibson backbone.fa
/export pMyGFP
```

**CLI** (same slash commands; chain with `--session-out`):

```bash
uv run crake cmd "/help"
uv run crake cmd "/load ./plasmid.gb" --session-out session.json
uv run crake cmd "/optimize e_coli" --session-out session.json
```

**Docker** (needs `.env` with `NCBI_EMAIL`, same as local):

```bash
cp .env.example .env   # edit NCBI_EMAIL
docker compose up --build
```

**Outputs** land in `./crake_output/`: GenBank and FASTA sequences, an SVG plasmid map, primer spreadsheet, and a human-readable protocol that records whether assembly was simulated or export was sequence-only.

---

## Commands (cheat sheet)

| Command | Plain English |
|---------|----------------|
| `/genesearch`, `/fetch`, `/load` | Find or load a DNA sequence |
| `/suggest`, `/optimize` | Suggest parts from the starter library; codon-tune for your host |
| `/targets`, `/annotate` | Find edit or cut sites; draw a restriction map |
| `/primers`, `/assemble` | Design PCR primers; simulate Gibson or restriction cloning |
| `/validate`, `/export` | Run checks; zip up files for the lab |
| `/introduce-gene` | Run the full pipeline in one go (also available as a sidebar form) |

Type `/help` in the app or see [docs/cli.md](docs/cli.md) for every flag.

---

## Tests

```bash
uv run pytest
uv run ruff check .
```

CI mocks NCBI so tests run offline. The **hero workflow** (`crake hero` / `tests/integration/test_hero_workflow.py`) regression-tests the full offline export bundle against a golden manifest.

---

## Project structure

```
crake/
├── app.py                 # Streamlit UI
├── src/
│   ├── agent/             # Slash commands → tool dispatch
│   ├── session/           # Workflow state (sequence → export)
│   ├── tools/             # Bioinformatics functions
│   ├── hero_workflow.py   # Offline demo pipeline (crake hero)
│   └── knowledge/         # Curated starter parts (JSON)
├── examples/hero/         # GFP CDS for hero demo
├── docs/scope.md          # What v1 promises
└── tests/
```

---

## Docs

- [Scope](docs/scope.md) — v1 boundary
- [Architecture](docs/architecture.md) — how session state and dispatch work
- [CLI](docs/cli.md) — `crake` slash commands
- [Roadmap](docs/roadmap.md)
- [Contributing](CONTRIBUTING.md)

---

## License

MIT
