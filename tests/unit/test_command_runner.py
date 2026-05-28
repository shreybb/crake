"""Tests for direct slash-command execution."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.agent.command_runner import execute_command


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
