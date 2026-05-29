#!/usr/bin/env bash
# Reproducible offline demo — same pipeline as CI (tests/integration/test_hero_workflow.py).
set -euo pipefail
cd "$(dirname "$0")/.."
uv run crake hero --output-dir ./crake_output/hero_demo
echo ""
echo "Open ./crake_output/hero_demo/protocol.md and pHeroGFP.gb in your viewer."
