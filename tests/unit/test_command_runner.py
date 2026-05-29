"""Tests for direct slash-command execution."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.agent.command_runner import execute_command, format_result_message


class TestExecuteCommand:
    def test_suggest_dispatches(self):
        session = {}
        with patch("src.agent.command_runner.dispatch") as mock_dispatch:
            mock_dispatch.return_value = {"recommended_backbones": [{"name": "pUC19"}]}
            tool, msg, result = execute_command("suggest", "e_coli", session)
        assert tool == "suggest_parts"
        assert mock_dispatch.call_args[0][0] == "suggest_parts"
        assert "pUC19" in msg or "panel" in msg.lower()
        assert result["recommended_backbones"]

    def test_optimize_requires_sequence(self):
        with pytest.raises(ValueError, match="No sequence loaded"):
            execute_command("optimize", "yeast", {})

    def test_fetch_builds_nucleotide_input(self):
        session = {}
        with patch("src.agent.command_runner.dispatch") as mock_dispatch:
            mock_dispatch.return_value = {"sequence": "ATG", "length_bp": 3}
            tool, _, _ = execute_command("fetch", "U55762", session)
        assert tool == "fetch_by_accession"
        assert mock_dispatch.call_args[0][1]["db"] == "nucleotide"

    def test_fetch_uniprot_accession(self):
        with patch("src.agent.command_runner.dispatch") as mock_dispatch:
            mock_dispatch.return_value = {"sequence_type": "protein"}
            execute_command("fetch", "P42212", {})
        assert mock_dispatch.call_args[0][1]["db"] == "uniprot"

    def test_introduce_gene_message_uses_vector_key(self):
        result = {
            "gene": "GFP",
            "target_host": "yeast",
            "cassette_description": "cassette",
            "optimized_sequence": "ATG",
            "vector": {"name": "pYES2"},
        }
        msg = format_result_message("introduce_gene", result)
        assert "pYES2" in msg
        assert "?" not in msg.split("Vector:")[-1][:5]

    def test_targets_crispr_forwards_pam(self):
        session = {"last_sequence": {"sequence": "ATCG" * 50, "topology": "linear"}}
        with patch("src.agent.command_runner.dispatch") as mock_dispatch:
            mock_dispatch.return_value = {"method": "crispr", "site_count": 0, "target_sites": []}
            tool, _, _ = execute_command("targets", "crispr TTTV", session)
        assert tool == "find_target_sites"
        assert mock_dispatch.call_args[0][1]["pam"] == "TTTV"

    def test_annotate_dispatches(self):
        session = {"last_sequence": {"sequence": "ATCG" * 20, "topology": "circular"}}
        with patch("src.agent.command_runner.dispatch") as mock_dispatch:
            mock_dispatch.return_value = {"restriction_sites": [], "site_count": 0}
            tool, msg, _ = execute_command("annotate", "", session)
        assert tool == "annotate_sequence"
        assert "Annotation" in msg

    def test_export_format_sequence_only_warning(self):
        msg = format_result_message(
            "export_files",
            {"genbank": "/tmp/x.gb", "provenance": "not_run"},
        )
        assert "sequence-only" in msg.lower() or "not simulated" in msg.lower()

    def test_validate_builds_input(self):
        session = {
            "last_sequence": {
                "sequence": "ATG" * 100,
                "gene_name": "gfp",
                "topology": "linear",
            },
        }
        with patch("src.agent.command_runner.dispatch") as mock_dispatch:
            mock_dispatch.return_value = {"passed_checks": True, "warnings": []}
            tool, _, _ = execute_command("validate", "", session)
        assert tool == "validate_plasmid"
        assert mock_dispatch.call_args[0][1]["name"] == "gfp"
