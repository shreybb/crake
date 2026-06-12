"""Extended _build_tool_input coverage."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.agent.command_runner import _build_tool_input


class TestBuildToolInputExtended:
    def test_load(self, tmp_path):
        gb = tmp_path / "x.gb"
        gb.write_text("LOCUS x\nORIGIN\n//\n")
        session = {}
        tool, inp = _build_tool_input("load", str(gb), session)
        assert tool == "import_sequence"

    def test_assemble_gibson(self):
        session = {"last_sequence": {"sequence": "ATCG" * 30}}
        tool, inp = _build_tool_input("assemble", "gibson other.fa", session)
        assert inp["method"] == "gibson"
        assert len(inp["fragments"]) == 2

    def test_assemble_restriction_ligation(self):
        session = {"last_sequence": {"sequence": "ATCG" * 30}}
        tool, inp = _build_tool_input(
            "assemble", "restriction_ligation EcoRI HindIII backbone.fa", session
        )
        assert inp["enzymes"] == ["EcoRI", "HindIII"]

    def test_primers_with_overhangs(self):
        session = {"last_sequence": {"sequence": "ATCG" * 50}}
        tool, inp = _build_tool_input("primers", "AAAA TTTT", session)
        assert inp["overhang_fwd"] == "AAAA"
        assert inp["overhang_rev"] == "TTTT"

    def test_introduce_gene(self):
        session = {}
        tool, inp = _build_tool_input(
            "introduce-gene", "GFP in Aequorea victoria into yeast", session
        )
        assert tool == "introduce_gene"
        assert inp["target_host"] == "yeast"

    def test_export_auto_validate(self):
        session = {
            "last_sequence": {
                "sequence": "ATG" * 50,
                "topology": "linear",
            },
        }
        with patch("src.agent.command_runner.dispatch") as mock:
            mock.return_value = {"passed_checks": True}
            tool, inp = _build_tool_input("export", "pX", session)
        assert tool == "export_files"
        mock.assert_called_once()

    def test_assemble_missing_method_raises(self):
        with pytest.raises(ValueError, match="Method must be"):
            _build_tool_input("assemble", "golden_gate x.fa", {})
