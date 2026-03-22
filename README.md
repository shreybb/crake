# Crake 🧬

**AI-assisted plasmid design.** Crake is a conversational interface for designing, annotating, and reasoning about plasmid sequences. It combines Claude's language understanding with a suite of bioinformatics tools — search, codon optimisation, primer design, assembly simulation, validation, and export — all accessible through natural language or slash commands.

---

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) package manager
- An Anthropic API key

---

## Installation

```bash
# Clone the repo
git clone https://github.com/your-org/crake.git
cd crake

# Install dependencies (uv handles the virtualenv automatically)
uv sync
```

---

## Environment Variables

Set the following before running:

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key — get one at [console.anthropic.com](https://console.anthropic.com) |

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Or create a `.env` file in the project root (Streamlit loads it automatically):

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Running

```bash
uv run streamlit run app.py
```

The app opens at `http://localhost:8501` by default.

---

## Running Tests

```bash
uv run python -m pytest
```

---

## Slash Commands

Type any of these in the chat input. All commands work on the sequence currently loaded in your session.

| Command | Description | Example |
|---|---|---|
| `/genesearch <query>` | Search NCBI for a gene by natural language | `/genesearch GFP jellyfish` |
| `/fetch <accession>` | Fetch a sequence by NCBI or UniProt accession | `/fetch NM_001234` |
| `/load <path>` | Load a sequence from a local file (`.dna`, `.gb`, `.fa`) | `/load /data/my_plasmid.gb` |
| `/suggest <host>` | Suggest vector backbones and regulatory parts for a host | `/suggest agrobacterium` |
| `/targets <method>` | Find edit target sites in the loaded sequence | `/targets crispr` |
| `/optimize <host>` | Codon-optimise the loaded sequence for a host | `/optimize plant_nuclear` |
| `/primers [overhangs]` | Design PCR primers for the loaded sequence | `/primers ATTB1 ATTB2` |
| `/assemble <method>` | Simulate in-vitro assembly | `/assemble gibson` |
| `/validate` | Validate the current construct | `/validate` |
| `/export <name>` | Export GenBank, FASTA, SVG map, primers CSV, and protocol | `/export pMyGFP` |
| `/help` | Show available commands | `/help` |

---

## Example Prompts

You can also use plain natural language — slash commands are just shortcuts.

```
Search for a fluorescent protein gene suitable for plant expression.
```

```
Fetch accession MN908947 and show me the sequence details.
```

```
Codon-optimise the loaded sequence for E. coli K-12, then design primers with BsaI overhangs.
```

```
Simulate a Gibson assembly with the current insert and pUC19 backbone, then validate it.
```

```
Export the final construct as pGFP-plant with all output files.
```

---

## Available Tools

Claude has access to the following tools during a conversation:

| Tool | What it does |
|---|---|
| `search_gene` | Searches NCBI for a gene by name and organism |
| `fetch_by_accession` | Retrieves a sequence by NCBI/UniProt accession |
| `import_sequence` | Loads a sequence from a local `.dna`, `.gb`, or `.fa` file |
| `suggest_parts` | Recommends vector backbones and parts for a given host |
| `find_target_sites` | Finds CRISPR PAM sites or restriction edit sites |
| `optimize_codons` | Codon-optimises a sequence for a target host |
| `design_primers` | Designs PCR primers with optional overhangs and Tm control |
| `simulate_assembly` | Simulates Gibson or restriction-ligation assembly |
| `validate_plasmid` | Checks the construct for common design issues |
| `export_files` | Writes GenBank, FASTA, SVG map, primers CSV, and protocol Markdown |

---

## Conversation History

- Conversations are auto-saved to `~/.crake/conversations/` when you click **Save**.
- Use the **sidebar** to browse and restore past sessions.
- Click **Export** to download a conversation as Markdown.

---

## Project Structure

```
crake/
├── app.py                  # Streamlit entry point
├── src/
│   ├── agent/
│   │   ├── commands.py     # Slash command definitions
│   │   ├── loop.py         # Claude agent turn loop
│   │   ├── tool_definitions.py
│   │   └── tool_dispatch.py
│   ├── tools/
│   │   ├── fetch_sequence.py
│   │   ├── import_file.py
│   │   ├── sequence_design.py
│   │   ├── target_site.py
│   │   ├── primer_design.py
│   │   ├── assembly.py
│   │   ├── validation.py
│   │   └── export.py
│   └── ui/
│       ├── components.py
│       └── styles.py
└── tests/
```
