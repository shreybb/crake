# Contributing

Thanks for helping improve Crake.

## Setup

```bash
git clone https://github.com/shreybb/crake.git
cd crake
uv sync
cp .env.example .env   # NCBI_EMAIL required for live fetch tests you run locally
```

## Tests

Run the full suite before opening a PR:

```bash
uv run pytest
```

Tests mock NCBI by default; no network required for CI.

## Adding a slash command

1. Define the command in `src/agent/commands.py` (`COMMANDS` + help text).
2. Parse args and build tool input in `src/agent/command_runner.py` (`_build_tool_input`).
3. Implement or reuse logic in `src/tools/` and wire in `src/agent/tool_dispatch.py`.
4. Add schema entry in `src/agent/tool_definitions.py` if it is a new tool name.
5. Add unit tests under `tests/unit/`.

## Code style

- Match existing patterns: small functions, dict-shaped tool results, `ValueError` for user-facing errors.
- Avoid new dependencies unless they clearly replace manual code.
- Do not commit secrets, `.env`, or personal `.mcp.json`.

## Biology changes

If you change codon tables, part recommendations, or validation heuristics, note the scientific rationale in the PR description. See `docs/audits/` for examples of prior review style.

## Questions

Open a [GitHub issue](https://github.com/shreybb/crake/issues) for bugs or feature discussion.
