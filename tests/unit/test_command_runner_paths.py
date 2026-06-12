"""Table-driven slash command parser tests."""

from __future__ import annotations

import pytest

from src.agent.command_runner import _build_tool_input, _normalize_host


class TestNormalizeHost:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("yeast", "yeast"),
            ("e.coli", "e_coli"),
            ("plant", "plant_nuclear"),
        ],
    )
    def test_aliases(self, raw, expected):
        assert _normalize_host(raw) == expected

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown host"):
            _normalize_host("mars")


class TestBuildToolInput:
    def test_genesearch(self):
        session = {
            "last_sequence": {"sequence": "ATG", "gene_name": "x"},
        }
        tool, inp = _build_tool_input("genesearch", "GFP in Aequorea victoria", session)
        assert tool == "search_gene"
        assert inp["gene_name"] == "GFP"

    def test_export_allow_sequence_only(self):
        session = {
            "last_sequence": {"sequence": "ATGAAATGA", "topology": "linear"},
            "last_validation": {"passed_checks": True},
        }
        tool, inp = _build_tool_input("export", "--allow-sequence-only pTest", session)
        assert tool == "export_files"
        assert inp["name"] == "pTest"
        assert inp["allow_sequence_only"] is True

    def test_annotate(self):
        session = {
            "last_sequence": {"sequence": "ATGAAATGA", "topology": "circular"},
        }
        tool, inp = _build_tool_input("annotate", "", session)
        assert tool == "annotate_sequence"
        assert inp["topology"] == "circular"

    def test_no_sequence_raises(self):
        with pytest.raises(ValueError, match="No sequence loaded"):
            _build_tool_input("optimize", "yeast", {})
