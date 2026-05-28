"""Unit tests for primer_design tool."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from src.tools.primer_design import design_primers, gc_content, melting_temperature


# A real 300-bp template (based on GFP partial sequence) for primer3 to work with.
TEMPLATE = (
    "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAGCTGGAC"
    "GGCGACGTAAACGGCCACAAGTTCAGCGTGTCCGGCGAGGGCGAGGGCGATGCCACCTAC"
    "GGCAAGCTGACCCTGAAGTTCATCTGCACCACCGGCAAGCTGCCCGTGCCCTGGCCCACC"
    "CTCGTGACCACCCTGACCTACGGCGTGCAGTGCTTCAGCCGCTACCCCGACCACATGAAG"
    "CAGCACGACTTCTTCAAGTCCGCCATGCCCGAAGGCTACGTCCAGGAGCGCACCATCTTC"
)  # 300 bp


# ---------------------------------------------------------------------------
# gc_content
# ---------------------------------------------------------------------------

class TestGcContent:
    def test_pure_gc(self):
        assert gc_content("GCGCGC") == 100.0

    def test_pure_at(self):
        assert gc_content("ATATAT") == 0.0

    def test_mixed(self):
        assert gc_content("ATGC") == 50.0

    def test_lowercase_input(self):
        assert gc_content("atgc") == 50.0

    def test_empty_returns_zero(self):
        assert gc_content("") == 0.0

    def test_returns_float(self):
        result = gc_content("ATCG")
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# melting_temperature
# ---------------------------------------------------------------------------

class TestMeltingTemperature:
    def test_returns_float(self):
        tm = melting_temperature("ATGCATGCATGCATGC")
        assert isinstance(tm, float)

    def test_gc_rich_higher_tm(self):
        tm_gc = melting_temperature("GCGCGCGCGCGCGCGC")
        tm_at = melting_temperature("ATATATATATATATAT")
        assert tm_gc > tm_at

    def test_rounded_to_one_decimal(self):
        tm = melting_temperature("ATGCATGCATGC")
        # Check it's a single decimal place float
        assert tm == round(tm, 1)


# ---------------------------------------------------------------------------
# design_primers
# ---------------------------------------------------------------------------

class TestDesignPrimers:
    def test_returns_template_length(self):
        result = design_primers(TEMPLATE)
        assert result["template_length"] == len(TEMPLATE)

    def test_overhangs_applied_in_result(self):
        result = design_primers(TEMPLATE, overhang_fwd="GCGC", overhang_rev="TATA")
        assert result["overhangs_applied"]["forward"] == "GCGC"
        assert result["overhangs_applied"]["reverse"] == "TATA"

    def test_primer_pairs_is_list(self):
        result = design_primers(TEMPLATE)
        assert isinstance(result["primer_pairs"], list)

    def test_primer_pair_has_required_keys(self):
        result = design_primers(TEMPLATE)
        if result["primer_pairs"]:
            pair = result["primer_pairs"][0]
            assert "forward" in pair
            assert "reverse" in pair
            assert "product_size_bp" in pair

    def test_overhang_prepended_to_full_sequence(self):
        overhang = "AAAA"
        result = design_primers(TEMPLATE, overhang_fwd=overhang)
        if result["primer_pairs"]:
            fwd = result["primer_pairs"][0]["forward"]
            assert fwd["full_sequence"].startswith(overhang)

    def test_primer_length_includes_overhang(self):
        overhang = "GCGCGCGC"
        result = design_primers(TEMPLATE, overhang_fwd=overhang)
        if result["primer_pairs"]:
            fwd = result["primer_pairs"][0]["forward"]
            assert fwd["length"] == len(fwd["full_sequence"])

    def test_custom_opt_tm(self):
        # Should not raise; just verifies parameter threading
        result = design_primers(TEMPLATE, opt_tm=55.0)
        assert "primer_pairs" in result

    def test_mocked_primer3_returns_pairs(self):
        mock_result = {
            "PRIMER_PAIR_NUM_RETURNED": 1,
            "PRIMER_LEFT_0_SEQUENCE": "ATGGTGAGCAAGGGCGAGG",
            "PRIMER_RIGHT_0_SEQUENCE": "CTTATGGTCGGGTAGCGGC",
            "PRIMER_LEFT_0_TM": 61.3,
            "PRIMER_RIGHT_0_TM": 60.8,
            "PRIMER_LEFT_0_GC_PERCENT": 57.9,
            "PRIMER_RIGHT_0_GC_PERCENT": 57.9,
            "PRIMER_PAIR_0_PRODUCT_SIZE": 200,
            "PRIMER_PAIR_0_PENALTY": 0.124,
        }
        with patch("src.tools.primer_design.primer3.design_primers", return_value=mock_result):
            result = design_primers("ATCG" * 50)

        assert len(result["primer_pairs"]) == 1
        pair = result["primer_pairs"][0]
        assert pair["rank"] == 0
        assert pair["forward"]["binding_region"] == "ATGGTGAGCAAGGGCGAGG"
        assert pair["reverse"]["tm_celsius"] == 60.8

    def test_zero_pairs_returned(self):
        mock_result = {"PRIMER_PAIR_NUM_RETURNED": 0}
        with patch("src.tools.primer_design.primer3.design_primers", return_value=mock_result):
            result = design_primers("ATCG" * 50)
        assert result["primer_pairs"] == []

    def test_warning_is_none_when_pairs_found(self):
        mock_result = {
            "PRIMER_PAIR_NUM_RETURNED": 1,
            "PRIMER_LEFT_0_SEQUENCE": "ATGGTGAGCAAGGGCGAGG",
            "PRIMER_RIGHT_0_SEQUENCE": "CTTATGGTCGGGTAGCGGC",
            "PRIMER_LEFT_0_TM": 61.3,
            "PRIMER_RIGHT_0_TM": 60.8,
            "PRIMER_LEFT_0_GC_PERCENT": 57.9,
            "PRIMER_RIGHT_0_GC_PERCENT": 57.9,
            "PRIMER_PAIR_0_PRODUCT_SIZE": 200,
            "PRIMER_PAIR_0_PENALTY": 0.124,
        }
        with patch("src.tools.primer_design.primer3.design_primers", return_value=mock_result):
            result = design_primers("ATCG" * 50)
        assert result["warning"] is None

    def test_warning_present_when_no_pairs(self):
        mock_result = {"PRIMER_PAIR_NUM_RETURNED": 0}
        with patch("src.tools.primer_design.primer3.design_primers", return_value=mock_result):
            result = design_primers("ATCG" * 50)
        assert result["warning"] is not None
        assert isinstance(result["warning"], str)
        assert len(result["warning"]) > 0

    def test_warning_includes_gc_percent(self):
        """Warning message should include the template GC% to aid diagnosis."""
        mock_result = {"PRIMER_PAIR_NUM_RETURNED": 0}
        with patch("src.tools.primer_design.primer3.design_primers", return_value=mock_result):
            result = design_primers("GCGCGCGC" * 10)  # 100% GC template
        assert "GC" in result["warning"] or "gc" in result["warning"].lower()

    def test_max_gc_is_70(self):
        """Confirm that primer3 is invoked with PRIMER_MAX_GC=70 (not 65)."""
        captured = {}
        original = __import__("primer3")

        def capture_call(seq_args, global_args):
            captured["global_args"] = global_args
            return {"PRIMER_PAIR_NUM_RETURNED": 0}

        with patch("src.tools.primer_design.primer3.design_primers", side_effect=capture_call):
            design_primers("ATCG" * 50)

        assert captured["global_args"]["PRIMER_MAX_GC"] == 70.0
