"""Unit tests for the gene introduction pipeline.

All NCBI and DNA-Chisel calls are mocked — no network or compute required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.tools.gene_introduction import introduce_gene, _build_cassette_description, _build_next_steps
from src.tools.knowledge import (
    suggest_backbone,
    suggest_promoter,
    suggest_selectable_marker,
    suggest_terminator,
)
from src.tools.sequence_design import optimize_codons


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Minimal in-frame CDS (multiple of 3, starts ATG)
_GFP_CDS = "ATG" + "GGC" * 30 + "TGA"  # 96 bp synthetic CDS


def _fake_search_gene_ok(gene_name, source_organism, full_sequence=False):
    return {
        "gene_name": gene_name,
        "organism": source_organism,
        "sequence": _GFP_CDS,
        "length_bp": len(_GFP_CDS),
        "sequence_type": "CDS",
        "suggested_host": "e_coli",
    }


def _fake_optimize_codons_ok(sequence, host):
    # Return a trivially different sequence to prove optimisation ran
    return {
        "original_sequence": sequence,
        "optimized_sequence": sequence.replace("GGC", "GGT"),
        "host": host,
        "species_table": "Saccharomyces cerevisiae",
    }


def _fake_optimize_codons_error(sequence, host):
    return {"error": "Codon optimisation failed", "original_sequence": sequence}


def _fake_search_gene_error(gene_name, source_organism, full_sequence=False):
    return {"error": "No results found", "gene": gene_name}


# ---------------------------------------------------------------------------
# Knowledge base — yeast entries
# ---------------------------------------------------------------------------

class TestYeastKnowledge:
    def test_suggest_backbone_yeast_returns_results(self):
        results = suggest_backbone("yeast")
        assert isinstance(results, list)
        assert len(results) >= 1
        names = [r["name"] for r in results]
        assert "pRS316" in names or "pYES2" in names

    def test_suggest_promoter_yeast_returns_results(self):
        results = suggest_promoter("yeast")
        assert isinstance(results, list)
        assert len(results) >= 1
        names = [r["name"] for r in results]
        assert "GAL1" in names

    def test_suggest_terminator_yeast_returns_results(self):
        results = suggest_terminator("yeast")
        assert isinstance(results, list)
        assert len(results) >= 1
        names = [r["name"] for r in results]
        assert "CYC1tt" in names

    def test_suggest_selectable_marker_yeast_returns_results(self):
        results = suggest_selectable_marker("yeast")
        assert isinstance(results, list)
        assert len(results) >= 1
        names = [r["name"] for r in results]
        assert "URA3" in names

    def test_unknown_host_returns_empty(self):
        assert suggest_backbone("unknown_host") == []
        assert suggest_promoter("unknown_host") == []
        assert suggest_terminator("unknown_host") == []
        assert suggest_selectable_marker("unknown_host") == []


# ---------------------------------------------------------------------------
# Codon optimisation — yeast path
# ---------------------------------------------------------------------------

class TestYeastCodonOptimisation:
    def test_yeast_in_host_map(self):
        """optimize_codons must not fall back to e_coli for yeast sequences."""
        from src.tools.sequence_design import optimize_codons as _oc

        mock_instance = MagicMock()
        mock_instance.sequence = _GFP_CDS

        mock_module = MagicMock()
        mock_module.DnaOptimizationProblem.return_value = mock_instance
        mock_module.CodonOptimize.return_value = MagicMock()
        mock_module.EnforceTranslation.return_value = MagicMock()

        with patch.dict("sys.modules", {"dnachisel": mock_module}):
            result = _oc(_GFP_CDS, "yeast")

        # The species_table must reflect yeast, not e_coli
        assert result.get("species_table") == "Saccharomyces cerevisiae"

    def test_invalid_sequence_length_returns_error(self):
        from src.tools.sequence_design import optimize_codons as _oc
        result = _oc("ATCG", "yeast")  # length 4 — not divisible by 3
        assert "error" in result


# ---------------------------------------------------------------------------
# introduce_gene — happy path (yeast)
# ---------------------------------------------------------------------------

class TestIntroduceGeneYeast:
    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_returns_all_required_keys(self, mock_search, mock_opt):
        result = introduce_gene("GFP", "Aequorea victoria", "yeast")
        required_keys = {
            "gene", "source_organism", "target_host",
            "original_sequence", "optimized_sequence",
            "vector", "promoter", "terminator", "marker",
            "cassette_description", "next_steps",
        }
        assert required_keys.issubset(result.keys()), (
            f"Missing keys: {required_keys - result.keys()}"
        )

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_optimised_sequence_differs_from_original(self, mock_search, mock_opt):
        result = introduce_gene("GFP", "Aequorea victoria", "yeast")
        assert result["optimized_sequence"] != result["original_sequence"]

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_vector_is_dict_with_name(self, mock_search, mock_opt):
        result = introduce_gene("GFP", "Aequorea victoria", "yeast")
        assert isinstance(result["vector"], dict)
        assert "name" in result["vector"]

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_next_steps_is_list(self, mock_search, mock_opt):
        result = introduce_gene("GFP", "Aequorea victoria", "yeast")
        assert isinstance(result["next_steps"], list)
        assert len(result["next_steps"]) >= 3

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_expression_goal_included_in_cassette_description(self, mock_search, mock_opt):
        result = introduce_gene("GFP", "Aequorea victoria", "yeast", expression_goal="bioluminescence")
        assert "bioluminescence" in result["cassette_description"]

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_correct_host_stored(self, mock_search, mock_opt):
        result = introduce_gene("GFP", "Aequorea victoria", "yeast")
        assert result["target_host"] == "yeast"


# ---------------------------------------------------------------------------
# introduce_gene — e_coli path
# ---------------------------------------------------------------------------

class TestIntroduceGeneEColi:
    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_ecoli_vector_suggested(self, mock_search, mock_opt):
        result = introduce_gene("lacZ", "Escherichia coli", "e_coli")
        assert "error" not in result
        assert result["vector"]["name"] in {"pET-28a", "pUC19", "pACYC184"}


# ---------------------------------------------------------------------------
# introduce_gene — error handling
# ---------------------------------------------------------------------------

class TestIntroduceGeneErrors:
    def test_invalid_host_returns_error(self):
        result = introduce_gene("GFP", "Aequorea victoria", "invalid_host")
        assert "error" in result
        assert "invalid_host" in result["error"]

    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_error)
    def test_ncbi_failure_returns_error(self, mock_search):
        result = introduce_gene("FAKEGENE", "Unknown organism", "yeast")
        assert "error" in result
        assert "Gene fetch failed" in result["error"]

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_error)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_codon_optimisation_failure_falls_back_to_original(self, mock_search, mock_opt):
        """When codon optimisation fails, original sequence should be used."""
        result = introduce_gene("GFP", "Aequorea victoria", "yeast")
        assert "error" not in result
        assert result["optimized_sequence"] == result["original_sequence"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_build_cassette_description_contains_parts(self):
        desc = _build_cassette_description(
            gene="GFP", host="yeast",
            promoter_name="GAL1", terminator_name="CYC1tt",
            vector_name="pYES2", marker_name="URA3",
            expression_goal="fluorescence",
        )
        assert "GAL1" in desc
        assert "CYC1tt" in desc
        assert "pYES2" in desc
        assert "URA3" in desc
        assert "fluorescence" in desc

    def test_build_next_steps_returns_ordered_list(self):
        steps = _build_next_steps("yeast", "pYES2", "URA3")
        assert isinstance(steps, list)
        assert any("codon" in s.lower() or "synthesise" in s.lower() for s in steps)


# ---------------------------------------------------------------------------
# Tool dispatch integration
# ---------------------------------------------------------------------------

class TestIntroduceGeneDispatch:
    @patch("src.agent.tool_dispatch._introduce_gene")
    def test_dispatch_routes_to_introduce_gene(self, mock_fn):
        from src.agent.tool_dispatch import dispatch
        mock_fn.return_value = {
            "gene": "GFP",
            "optimized_sequence": _GFP_CDS,
            "source_organism": "Aequorea victoria",
            "target_host": "yeast",
            "vector": {"name": "pYES2"},
            "promoter": {"name": "GAL1"},
            "terminator": {"name": "CYC1tt"},
            "marker": {"name": "URA3"},
            "cassette_description": "test",
            "next_steps": [],
        }
        session = {}
        result = dispatch(
            "introduce_gene",
            {
                "gene_name": "GFP",
                "source_organism": "Aequorea victoria",
                "target_host": "yeast",
            },
            session,
        )
        mock_fn.assert_called_once_with(
            gene_name="GFP",
            source_organism="Aequorea victoria",
            target_host="yeast",
            expression_goal="",
        )
        assert result["gene"] == "GFP"

    @patch("src.agent.tool_dispatch._introduce_gene")
    def test_dispatch_stores_result_in_session(self, mock_fn):
        from src.agent.tool_dispatch import dispatch
        mock_fn.return_value = {
            "gene": "GFP",
            "optimized_sequence": _GFP_CDS,
            "source_organism": "Aequorea victoria",
            "target_host": "yeast",
            "vector": {"name": "pYES2"},
            "promoter": {"name": "GAL1"},
            "terminator": {"name": "CYC1tt"},
            "marker": {"name": "URA3"},
            "cassette_description": "test",
            "next_steps": [],
        }
        session = {}
        dispatch(
            "introduce_gene",
            {
                "gene_name": "GFP",
                "source_organism": "Aequorea victoria",
                "target_host": "yeast",
            },
            session,
        )
        assert "last_gene_introduction" in session
        assert session["last_sequence"]["sequence"] == _GFP_CDS
