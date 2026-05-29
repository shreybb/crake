# Benchling (optional MCP)

Benchling integration is **not part of Crake v1**. This document describes an optional external workflow for users who already use Benchling.

## Setup

1. Copy `.mcp.json.example` to `.mcp.json` (gitignored).
2. Configure the Playwright MCP server with a dedicated browser profile.
3. Log into Benchling manually on first run; the profile reuses the session.

## Usage

External AI agents (Cursor, Claude Code, etc.) can use the MCP browser to interact with Benchling while Crake produces local artifacts in `./crake_output/`.

Crake does not sync sequences, primers, or constructs to Benchling automatically. Import/export remains manual: upload GenBank/FASTA from Crake export, or download from Benchling and `/load` into Crake.

## Non-goals

- In-app Benchling OAuth
- Automatic construct registration
- Bidirectional sync with `ConstructSession`
