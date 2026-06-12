"""Hero workflow: offline GFP → e_coli → export bundle (golden manifest)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.hero_workflow import run_hero_workflow

_GOLDEN = Path(__file__).resolve().parent.parent / "golden_fixtures" / "hero_export_manifest.json"


class TestHeroWorkflow:
    def test_export_manifest_matches_golden(self, tmp_path):
        manifest = run_hero_workflow(tmp_path)

        if os.environ.get("CRAKE_UPDATE_GOLDEN"):
            _GOLDEN.write_text(json.dumps(manifest, indent=2) + "\n")
            pytest.skip("hero golden manifest updated")

        expected = json.loads(_GOLDEN.read_text())
        assert manifest == expected

    def test_writes_all_export_artifacts(self, tmp_path):
        manifest = run_hero_workflow(tmp_path)
        for name in manifest["files"]:
            assert (tmp_path / name).is_file(), f"missing {name}"
        assert (tmp_path / "protocol.md").read_text().find("Sequence-only") >= 0
