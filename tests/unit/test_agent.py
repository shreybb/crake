"""Unit tests for the agent layer (tool_dispatch and loop).

No Streamlit, no real Anthropic API calls, no NCBI network requests.
All external calls are mocked.
"""
from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock

import pytest

from src.agent.tool_dispatch import dispatch
from src.agent.loop import run_agent_turn, extract_text_response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


# ---------------------------------------------------------------------------
# TestToolDispatch
# ---------------------------------------------------------------------------

class TestToolDispatch:
    def test_search_gene_calls_function_with_correct_args(self, mocker):
        mock_fn = mocker.patch(
            "src.agent.tool_dispatch._search_gene",
            return_value={"sequence": "ATG", "suggested_host": "agrobacterium"},
        )
        session = {}
        result = dispatch("search_gene", {"gene_name": "GFP", "organism": "Aequorea victoria"}, session)
        mock_fn.assert_called_once_with("GFP", "Aequorea victoria", full_sequence=False)
        assert result["sequence"] == "ATG"

    def test_dispatch_stores_sequence_in_session(self, mocker):
        mocker.patch(
            "src.agent.tool_dispatch._search_gene",
            return_value={"sequence": "ATCG", "suggested_host": "e_coli"},
        )
        session = {}
        dispatch("search_gene", {"gene_name": "lacZ", "organism": "Escherichia coli"}, session)
        assert session["last_sequence"]["sequence"] == "ATCG"

    def test_fetch_by_accession_stores_in_session(self, mocker):
        mocker.patch(
            "src.agent.tool_dispatch._fetch_by_accession",
            return_value={"sequence": "GCGC", "suggested_host": "e_coli"},
        )
        session = {}
        dispatch("fetch_by_accession", {"accession": "U55762"}, session)
        assert session["last_sequence"]["sequence"] == "GCGC"

    def test_optimize_codons_passes_sequence_and_host(self, mocker):
        mock_fn = mocker.patch(
            "src.agent.tool_dispatch._optimize_codons",
            return_value={"optimized_sequence": "ATG"},
        )
        dispatch("optimize_codons", {"sequence": "ATGATG", "host": "plant_nuclear"}, {})
        mock_fn.assert_called_once_with("ATGATG", "plant_nuclear")

    def test_suggest_parts_passes_host(self, mocker):
        mock_fn = mocker.patch(
            "src.agent.tool_dispatch._suggest_parts",
            return_value={"recommended_backbones": []},
        )
        dispatch("suggest_parts", {"host": "agrobacterium"}, {})
        mock_fn.assert_called_once_with("agrobacterium")

    def test_simulate_assembly_routes_gibson(self, mocker):
        mock_gibson = mocker.patch(
            "src.agent.tool_dispatch.simulate_gibson",
            return_value={"success": True, "product_sequence": "ATCG"},
        )
        mocker.patch("src.agent.tool_dispatch.simulate_restriction_ligation")
        session = {}
        dispatch("simulate_assembly", {"fragments": ["ATCG", "GCTA"], "method": "gibson"}, session)
        mock_gibson.assert_called_once_with(["ATCG", "GCTA"])
        assert session["last_assembly"]["success"] is True

    def test_simulate_assembly_routes_restriction_ligation(self, mocker):
        mocker.patch("src.agent.tool_dispatch.simulate_gibson")
        mock_rl = mocker.patch(
            "src.agent.tool_dispatch.simulate_restriction_ligation",
            return_value={"success": True, "product_sequence": "TTTT"},
        )
        session = {}
        dispatch(
            "simulate_assembly",
            {"fragments": ["ATCG"], "method": "restriction_ligation", "enzymes": ["EcoRI"]},
            session,
        )
        mock_rl.assert_called_once_with(["ATCG"], ["EcoRI"])

    def test_find_target_sites_restriction_method(self, mocker):
        mock_fn = mocker.patch(
            "src.agent.tool_dispatch.find_restriction_edit_sites",
            return_value=[{"enzyme": "EcoRI", "position": 100}],
        )
        result = dispatch("find_target_sites", {"sequence": "ATCG", "method": "restriction"}, {})
        mock_fn.assert_called_once()
        assert result["method"] == "restriction"
        assert result["site_count"] == 1

    def test_find_target_sites_crispr_method(self, mocker):
        mock_fn = mocker.patch(
            "src.agent.tool_dispatch.find_crispr_pam_sites",
            return_value=[{"guide_rna": "GCGCATCGATCGATCGATCG"}],
        )
        result = dispatch("find_target_sites", {"sequence": "ATCG" * 50, "method": "crispr"}, {})
        mock_fn.assert_called_once()
        assert result["method"] == "crispr"

    def test_find_target_sites_homologous_method(self, mocker):
        mock_fn = mocker.patch(
            "src.agent.tool_dispatch.extract_homology_arms",
            return_value={"left_arm": "AAAA", "right_arm": "TTTT", "position": 200},
        )
        result = dispatch(
            "find_target_sites",
            {"sequence": "ATCG" * 100, "method": "homologous", "position": 200},
            {},
        )
        mock_fn.assert_called_once()
        assert result["method"] == "homologous"

    def test_find_target_sites_homologous_missing_position(self):
        result = dispatch("find_target_sites", {"sequence": "ATCG", "method": "homologous"}, {})
        assert "error" in result

    def test_design_primers_stores_in_session(self, mocker):
        mocker.patch(
            "src.agent.tool_dispatch._design_primers",
            return_value={"primer_pairs": [{"rank": 0}]},
        )
        session = {}
        dispatch("design_primers", {"template": "ATCGATCG" * 10}, session)
        assert "primer_pairs" in session["last_primers"]

    def test_validate_plasmid_stores_in_session(self, mocker):
        mocker.patch(
            "src.agent.tool_dispatch._validate_plasmid",
            return_value={"valid": True, "warnings": []},
        )
        session = {}
        dispatch("validate_plasmid", {"sequence": "ATCG" * 100}, session)
        assert session["last_validation"]["valid"] is True

    def test_export_reads_from_session(self, mocker, tmp_path):
        session = {
            "last_assembly": {"product_sequence": "ATCGATCG" * 100, "topology": "circular", "method": "gibson", "input_parts": []},
            "last_validation": {"orfs": [], "restriction_sites": [], "warnings": [], "gc_analysis": {"overall_gc_percent": 50, "flagged_windows": []}},
            "last_primers": {"primer_pairs": []},
        }
        mocker.patch("src.agent.tool_dispatch.write_genbank", return_value=tmp_path / "x.gb")
        mocker.patch("src.agent.tool_dispatch.write_fasta", return_value=tmp_path / "x.fa")
        mocker.patch("src.agent.tool_dispatch.write_plasmid_map", return_value=tmp_path / "x.svg")
        mocker.patch("src.agent.tool_dispatch.write_primers_csv", return_value=tmp_path / "p.csv")
        mocker.patch("src.agent.tool_dispatch.write_protocol_md", return_value=tmp_path / "p.md")

        result = dispatch("export_files", {"name": "pTest", "output_dir": str(tmp_path)}, session)
        assert "export_paths" in session
        assert "genbank" in result

    def test_unknown_tool_raises_valueerror(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            dispatch("nonexistent_tool", {}, {})


# ---------------------------------------------------------------------------
# Helpers for subprocess-based loop tests
# ---------------------------------------------------------------------------

def _make_claude_output(text: str) -> MagicMock:
    """Simulate a successful `claude -p` subprocess result returning plain text."""
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = json.dumps({"result": text})
    proc.stderr = ""
    return proc


def _tool_call_text(name: str, inp: dict) -> str:
    return f'<tool_call>\n{json.dumps({"name": name, "input": inp})}\n</tool_call>'


# ---------------------------------------------------------------------------
# TestAgentLoop
# ---------------------------------------------------------------------------

class TestAgentLoop:
    def _mock_subprocess(self, mocker, outputs: list[str]):
        """Patch subprocess.run so it returns outputs in order."""
        procs = [_make_claude_output(o) for o in outputs]
        mocker.patch("src.agent.loop.subprocess.run", side_effect=procs)

    def test_no_tool_call_appends_message(self, mocker):
        self._mock_subprocess(mocker, ["Hello!"])

        history = []
        updated, log = run_agent_turn("Hi", history, {})
        assert len(updated) == 2  # user + assistant
        assert log == []

    def test_single_tool_call_dispatched_and_result_returned(self, mocker):
        self._mock_subprocess(mocker, [
            _tool_call_text("suggest_parts", {"host": "e_coli"}),
            "Here are the parts.",
        ])
        mock_dispatch = mocker.patch(
            "src.agent.loop.dispatch",
            return_value={"recommended_backbones": []},
        )

        history = []
        updated, log = run_agent_turn("Suggest E. coli parts", history, {})

        mock_dispatch.assert_called_once_with("suggest_parts", {"host": "e_coli"}, {})
        assert len(log) == 1
        assert log[0]["tool_name"] == "suggest_parts"
        # history: user, assistant(tool_use), user(tool_result), assistant(text)
        assert len(updated) == 4

    def test_multi_tool_call_loop_terminates(self, mocker):
        self._mock_subprocess(mocker, [
            _tool_call_text("search_gene", {"gene_name": "GFP", "organism": "test"}),
            _tool_call_text("validate_plasmid", {"sequence": "ATG"}),
            "Done.",
        ])
        mocker.patch("src.agent.loop.dispatch", return_value={})

        history = []
        updated, log = run_agent_turn("Design a construct", history, {})
        assert len(log) == 2
        assert log[0]["tool_name"] == "search_gene"
        assert log[1]["tool_name"] == "validate_plasmid"

    def test_tool_calls_log_populated_with_results(self, mocker):
        self._mock_subprocess(mocker, [
            _tool_call_text("suggest_parts", {"host": "agrobacterium"}),
            "Done.",
        ])
        fake_result = {"recommended_backbones": [{"name": "pCAMBIA1300"}]}
        mocker.patch("src.agent.loop.dispatch", return_value=fake_result)

        _, log = run_agent_turn("Suggest parts", [], {})
        assert log[0]["result"] == fake_result

    def test_dispatch_error_stored_in_log(self, mocker):
        self._mock_subprocess(mocker, [
            _tool_call_text("bad_tool", {}),
            "Error handled.",
        ])
        mocker.patch("src.agent.loop.dispatch", side_effect=ValueError("Unknown tool"))

        _, log = run_agent_turn("Do bad thing", [], {})
        assert "error" in log[0]["result"]

    def test_conversation_history_updated_in_place(self, mocker):
        self._mock_subprocess(mocker, ["Hi!"])

        history = []
        run_agent_turn("Hello", history, {})
        # History is mutated in place AND returned
        assert len(history) == 2

    def test_subprocess_error_raises_runtime_error(self, mocker):
        proc = MagicMock()
        proc.returncode = 1
        proc.stderr = "auth error"
        mocker.patch("src.agent.loop.subprocess.run", return_value=proc)

        with pytest.raises(RuntimeError, match="claude process error"):
            run_agent_turn("Hello", [], {})


# ---------------------------------------------------------------------------
# TestExtractTextResponse
# ---------------------------------------------------------------------------

class TestExtractTextResponse:
    def test_extracts_last_text_block(self):
        block = _make_text_block("Final answer.")
        history = [{"role": "assistant", "content": [block]}]
        assert extract_text_response(history) == "Final answer."

    def test_skips_non_assistant_messages(self):
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": [_make_text_block("reply")]},
        ]
        assert extract_text_response(history) == "reply"

    def test_empty_history_returns_empty_string(self):
        assert extract_text_response([]) == ""
