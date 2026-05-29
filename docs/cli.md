# Command-line interface

Crake exposes one scripting surface: the **`crake` Typer CLI**. It uses the same `tool_dispatch` layer as the Streamlit app (no shell-outs to tool modules).

## Setup

```bash
uv sync
uv run crake --help
```

## Slash commands (ephemeral session)

```bash
uv run crake cmd "/genesearch GFP in Aequorea victoria"
uv run crake cmd "/fetch U55762"
uv run crake cmd "/load ./plasmid.gb"
uv run crake cmd "/optimize yeast" --session-out ./session.json
uv run crake cmd "/validate"
uv run crake cmd "/annotate"
uv run crake cmd "/primers"
uv run crake cmd "/assemble gibson backbone.fa"
uv run crake cmd "/export pMyGFP"
uv run crake cmd "/export pMyGFP --allow-sequence-only"
```

Persist workflow state with `--session-out` and resume with the session subcommands below.

## Session file workflow

```bash
uv run crake session run ./session.json "/validate"
uv run crake session export ./session.json --name pMyGFP --output-dir ./crake_output
```

## Streamlit

```bash
uv run streamlit run app.py
```

See [README.md](../README.md) for the full command list (`/help` in the app).

## Environment

Set `NCBI_EMAIL` (and optionally `NCBI_API_KEY`) before fetch commands. See `.env.example`.
