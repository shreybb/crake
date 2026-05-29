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
uv run ruff check .
uv run pytest --cov=src/agent --cov=src/session --cov-fail-under=85
```

Tests mock NCBI by default; no network required for CI.

Update golden fixtures when intentional output changes:

```bash
CRAKE_UPDATE_GOLDEN=1 uv run pytest tests/unit/test_golden_gfp_chain.py -q
CRAKE_UPDATE_GOLDEN=1 uv run pytest tests/integration/test_hero_workflow.py -q
```

## Adding a slash command

1. Define the command in `src/agent/commands.py` (`COMMANDS` + help text).
2. Parse args and build tool input in `src/agent/command_runner.py` (`_build_tool_input`).
3. Implement or reuse logic in `src/tools/` and wire in `src/agent/tool_dispatch.py`.
4. Update `ConstructSession` in `src/session/construct.py` if the command changes workflow state.
5. Add schema entry in `src/agent/tool_definitions.py` if it is a new tool name.
6. Add unit tests under `tests/unit/`.

Session and export changes must note **provenance** impact in the PR description.

## Code style

- Match existing patterns: small functions, dict-shaped tool results, `ValueError` for user-facing errors.
- Avoid new dependencies unless they clearly replace manual code.
- Do not commit secrets or `.env` files.

## Biology changes

If you change codon tables, part recommendations, or validation heuristics, note the scientific rationale in the PR description. See `docs/audits/` for examples of prior review style.

## Questions

Open a [GitHub issue](https://github.com/shreybb/crake/issues) for bugs or feature discussion.
