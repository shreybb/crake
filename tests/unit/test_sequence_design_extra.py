"""Additional unit tests for sequence_design tool (codon optimization)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.tools.sequence_design import analyze_sequence, optimize_codons

# Minimal valid CDS (length divisible by 3, starts with ATG)
MINI_CDS = "ATGGAATTCAAATGA"  # 15 bp, translates to MEFS*


def _mock_dnachisel(mock_problem: MagicMock):
    """Patch the lazy dnachisel imports inside optimize_codons."""
    mock_module = MagicMock()
    mock_module.DnaOptimizationProblem = MagicMock(return_value=mock_problem)
    mock_module.CodonOptimize = MagicMock()
    mock_module.EnforceTranslation = MagicMock()
    return patch.dict("sys.modules", {"dnachisel": mock_module})


class TestOptimizeCodons:
    def test_non_frame_sequence_returns_error(self):
        result = optimize_codons("ATGGATCG", "e_coli")  # 8 bp, not divisible by 3
        assert "error" in result

    def test_valid_cds_returns_optimized_sequence(self):
        mock_problem = MagicMock()
        mock_problem.sequence = "ATGGAGTTTAAATGA"

        with _mock_dnachisel(mock_problem):
            result = optimize_codons(MINI_CDS, "e_coli")

        assert result["original_sequence"] == MINI_CDS
        assert "optimized_sequence" in result
        assert result["host"] == "e_coli"

    def test_plant_nuclear_host_maps_to_arabidopsis(self):
        mock_problem = MagicMock()
        mock_problem.sequence = MINI_CDS

        with _mock_dnachisel(mock_problem):
            optimize_codons(MINI_CDS, "plant_nuclear")

        assert mock_problem.resolve_constraints.called

    def test_unknown_host_defaults_to_ecoli(self):
        mock_problem = MagicMock()
        mock_problem.sequence = MINI_CDS

        with _mock_dnachisel(mock_problem):
            result = optimize_codons(MINI_CDS, "unknown_host")

        assert isinstance(result, dict)

    def test_optimization_exception_returns_error(self):
        mock_problem = MagicMock()
        mock_problem.resolve_constraints.side_effect = RuntimeError("failed")

        with _mock_dnachisel(mock_problem):
            result = optimize_codons(MINI_CDS, "e_coli")

        assert "error" in result
        assert result["original_sequence"] == MINI_CDS

    def test_result_includes_gc_analysis(self):
        mock_problem = MagicMock()
        mock_problem.sequence = MINI_CDS

        with _mock_dnachisel(mock_problem):
            result = optimize_codons(MINI_CDS, "e_coli")

        assert "gc_before" in result
        assert "gc_after" in result
        assert "analysis" in result

    def test_agrobacterium_host_maps_to_arabidopsis_table(self):
        mock_problem = MagicMock()
        mock_problem.sequence = MINI_CDS

        with _mock_dnachisel(mock_problem):
            result = optimize_codons(MINI_CDS, "agrobacterium")

        assert result.get("species_table") == "3702"


class TestOptimizeCodonsIntegration:
    """Real DnaChisel runs (no mocks) — catches broken codon table names."""

    def test_e_coli_optimize_runs(self):
        result = optimize_codons(MINI_CDS, "e_coli")
        assert "error" not in result
        assert result["species_table"] == "e_coli"
        assert len(result["optimized_sequence"]) == len(MINI_CDS)

    def test_yeast_optimize_runs(self):
        result = optimize_codons(MINI_CDS, "yeast")
        assert "error" not in result
        assert result["species_table"] == "s_cerevisiae_4932"

    def test_plant_host_uses_arabidopsis_taxon_table(self):
        result = optimize_codons(MINI_CDS, "plant_nuclear")
        assert "error" not in result
        assert result["species_table"] == "3702"


class TestAnalyzeSequenceExtra:
    def test_empty_sequence_returns_zeros(self):
        result = analyze_sequence("")
        assert result["length_bp"] == 0
        assert result["gc_content_percent"] == 0
        assert result["at_content_percent"] == 0

    def test_base_counts_correct(self):
        result = analyze_sequence("AATCG")
        assert result["base_counts"]["A"] == 2
        assert result["base_counts"]["T"] == 1
        assert result["base_counts"]["C"] == 1
        assert result["base_counts"]["G"] == 1

    def test_n_counted(self):
        result = analyze_sequence("ATCGN")
        assert result["base_counts"]["N"] == 1
