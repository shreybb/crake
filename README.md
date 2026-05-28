# Crake

**Plasmid design workbench** — fetch genes, codon-optimise for a host, suggest curated vector parts, validate constructs, and export lab-ready files (GenBank, FASTA, primer CSV, SVG map, protocol). **No LLM or API keys required.**

---

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) package manager

---

## Installation

```bash
git clone https://github.com/your-org/crake.git
cd crake
uv sync
```

---

## Running

```bash
uv run streamlit run app.py
```

Opens at `http://localhost:8501`.

Use the sidebar **Introduce a Gene** form or type slash commands in the chat box (`/help` for the list).

---

## Running Tests

```bash
uv run pytest
```

---

## Commands

All commands run **deterministic Python tools** (NCBI, DnaChisel, Primer3, etc.).

| Command | Description | Example |
|---|---|---|
| `/genesearch <gene> in <organism>` | Search NCBI for a CDS | `/genesearch GFP in Aequorea victoria` |
| `/fetch <accession>` | NCBI or UniProt accession | `/fetch U55762` or `/fetch P42212` |
| `/load <path>` | Import `.dna`, `.gb`, or `.fa` | `/load ./plasmid.gb` |
| `/suggest <host>` | Parts for a host | `/suggest yeast` |
| `/targets <method>` | CRISPR / restriction / homologous sites | `/targets crispr` |
| `/optimize <host>` | Codon-optimise loaded sequence | `/optimize plant_nuclear` |
| `/primers [overhangs]` | PCR primers for loaded sequence | `/primers ATTB1 ATTB2` |
| `/assemble gibson <file>` | Gibson assembly (2 fragments) | `/assemble gibson backbone.fa` |
| `/validate` | ORFs, GC, restriction map | `/validate` |
| `/export <name>` | Write GenBank, FASTA, map, CSV, protocol | `/export pMyGFP` |
| `/introduce-gene …` | Fetch → optimise → suggest parts | see sidebar form |
| `/help` | Command reference | `/help` |

**Hosts:** `e_coli`, `yeast`, `plant_nuclear`, `agrobacterium`

---

## Project Structure

```
crake/
├── app.py                      # Streamlit UI
├── src/
│   ├── agent/
│   │   ├── command_runner.py   # Slash command → tool dispatch
│   │   ├── commands.py         # Command definitions
│   │   ├── tool_dispatch.py    # Tool router + session state
│   │   └── tool_definitions.py # Input schemas (tests/docs)
│   ├── tools/                  # Bioinformatics implementations
│   ├── knowledge/              # Curated parts JSON
│   └── ui/
└── tests/
```

---

## Session & export

- Tool results update the right-hand panel (sequence, primers, validation).
- `/export` writes to `./crake_output/` by default.
- Conversations can be saved from the UI to `~/.crake/conversations/`.
