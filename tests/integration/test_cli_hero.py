"""CLI tests: crake hero and crake cmd session chain."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from typer.testing import CliRunner

from src.cli import app
from src.hero_workflow import run_hero_workflow

runner = CliRunner()


def _fasta_sha256(path: Path) -> str:
    seq = "".join(
        ln.strip()
        for ln in path.read_text().splitlines()
        if not ln.startswith(">")
    ).upper()
    return hashlib.sha256(seq.encode()).hexdigest()


class TestCrakeHeroCommand:
    def test_hero_writes_export_bundle(self, tmp_path):
        out = tmp_path / "out"
        result = runner.invoke(app, ["hero", "--output-dir", str(out)])
        assert result.exit_code == 0, result.stdout + result.stderr
        assert (out / "pHeroGFP.fa").is_file()
        assert "pHeroGFP" in result.stdout

    def test_hero_cli_matches_library_manifest(self, tmp_path):
        out_cli = tmp_path / "cli"
        out_lib = tmp_path / "lib"
        result = runner.invoke(app, ["hero", "--output-dir", str(out_cli)])
        assert result.exit_code == 0
        lib_manifest = run_hero_workflow(out_lib)
        cli_files = sorted(p.name for p in out_cli.iterdir() if p.is_file())
        assert cli_files == lib_manifest["files"]
        assert _fasta_sha256(out_cli / "pHeroGFP.fa") == lib_manifest["sequence_sha256"]


class TestCrakeCmdChain:
    def test_cmd_load_optimize_validate_session_out(self, tmp_path):
        gfp = Path(__file__).resolve().parents[2] / "examples" / "hero" / "gfp_cds.fa"
        session = tmp_path / "session.json"
        steps = [
            f"/load {gfp}",
            "/optimize e_coli",
            "/validate",
        ]
        for cmd in steps:
            result = runner.invoke(
                app,
                ["cmd", cmd, "--session-out", str(session)],
            )
            assert result.exit_code == 0, f"{cmd}: {result.stdout} {result.stderr}"
        assert session.is_file()
        data = json.loads(session.read_text())
        assert data.get("last_sequence", {}).get("sequence")
        assert data.get("last_validation")
