"""Unit tests for the gene introduction pipeline.

All NCBI and DNA-Chisel calls are mocked — no network or compute required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.tools.gene_introduction import (
    introduce_gene,
    _build_cassette_description,
    _build_next_steps,
    _infer_expression_type,
    _pick_backbone,
    _pick_promoter,
)
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
        "species_table": "s_cerevisiae_4932",
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
        assert result.get("species_table") == "s_cerevisiae_4932"

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

    def test_agrobacterium_in_valid_hosts_set(self):
        """Issue I fix: agrobacterium must be in _VALID_HOSTS so plant T-DNA workflows work."""
        from src.tools.gene_introduction import _VALID_HOSTS
        assert "agrobacterium" in _VALID_HOSTS

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


class TestYeastSelectionMedia:
    """Verify that _build_next_steps emits correct selection media for each yeast marker.

    Dropout media are named for the NUTRIENT omitted (SC-URA / SC-LEU / SC-HIS / SC-TRP),
    not for the marker gene (URA3 / LEU2 / HIS3 / TRP1).
    Dominant antibiotic markers (kanMX, hygMX) require YPD + antibiotic — no SC dropout.
    """

    def _steps_text(self, marker: str) -> str:
        return " ".join(_build_next_steps("yeast", "pRS316", marker))

    # --- auxotrophic markers: must use nutrient-named dropout ---
    def test_ura3_uses_SC_URA_not_gene_name(self):
        txt = self._steps_text("URA3")
        assert "SC-URA" in txt, f"Expected 'SC-URA' in steps: {txt}"
        assert "SC-URA3" not in txt, "Should not write 'SC-URA3' (wrong notation)"

    def test_leu2_uses_SC_LEU_not_gene_name(self):
        txt = self._steps_text("LEU2")
        assert "SC-LEU" in txt
        assert "SC-LEU2" not in txt

    def test_his3_uses_SC_HIS_not_gene_name(self):
        txt = self._steps_text("HIS3")
        assert "SC-HIS" in txt
        assert "SC-HIS3" not in txt

    def test_trp1_uses_SC_TRP_not_gene_name(self):
        txt = self._steps_text("TRP1")
        assert "SC-TRP" in txt
        assert "SC-TRP1" not in txt

    # --- dominant antibiotic markers: must NOT reference SC dropout ---
    def test_kanMX_uses_G418_not_SC_dropout(self):
        txt = self._steps_text("kanMX")
        assert "G418" in txt, f"Expected 'G418' in steps: {txt}"
        assert "SC-kanMX" not in txt, "kanMX uses YPD+G418, not SC dropout"

    def test_hygMX_uses_hygromycin_not_SC_dropout(self):
        txt = self._steps_text("hygMX")
        assert "Hygromycin" in txt or "hygromycin" in txt
        assert "SC-hygMX" not in txt, "hygMX uses YPD+HygB, not SC dropout"


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


# ---------------------------------------------------------------------------
# Promoter expression type inference
# ---------------------------------------------------------------------------

class TestInferExpressionType:
    def test_constitutive_keyword(self):
        assert _infer_expression_type("constitutive expression") == "constitutive"

    def test_inducible_keyword(self):
        assert _infer_expression_type("inducible overexpression") == "inducible"

    def test_galactose_implies_inducible(self):
        assert _infer_expression_type("galactose-induced") == "inducible"

    def test_iptg_implies_inducible(self):
        assert _infer_expression_type("IPTG induction") == "inducible"

    def test_strong_constitutive(self):
        assert _infer_expression_type("strong constitutive") == "constitutive"

    def test_empty_goal_returns_none(self):
        assert _infer_expression_type("") is None

    def test_unrelated_goal_returns_none(self):
        assert _infer_expression_type("bioluminescence") is None


# ---------------------------------------------------------------------------
# Promoter picking by expression type
# ---------------------------------------------------------------------------

_YEAST_PROMOTERS = [
    {"name": "GAL1", "expression_type": "inducible", "strength": "very_high"},
    {"name": "TEF1", "expression_type": "constitutive", "strength": "high"},
    {"name": "TDH3", "expression_type": "constitutive", "strength": "very_high"},
    {"name": "ADH1", "expression_type": "constitutive", "strength": "medium"},
]


class TestPickPromoter:
    def test_constitutive_excludes_gal1(self):
        result = _pick_promoter(_YEAST_PROMOTERS, "constitutive")
        assert result["name"] != "GAL1"

    def test_constitutive_returns_constitutive_type(self):
        result = _pick_promoter(_YEAST_PROMOTERS, "constitutive")
        assert result["expression_type"] == "constitutive"

    def test_inducible_returns_gal1(self):
        result = _pick_promoter(_YEAST_PROMOTERS, "inducible")
        assert result["name"] == "GAL1"

    def test_fallback_when_no_match(self):
        result = _pick_promoter(_YEAST_PROMOTERS, "repressible")
        assert result["name"] == "GAL1"  # falls back to first

    def test_none_type_returns_first(self):
        result = _pick_promoter(_YEAST_PROMOTERS, None)
        assert result["name"] == "GAL1"  # first item

    def test_empty_list_returns_none(self):
        result = _pick_promoter([], "constitutive")
        assert result is None


# ---------------------------------------------------------------------------
# introduce_gene — expression goal drives promoter selection
# ---------------------------------------------------------------------------

class TestIntroduceGenePromoterSelection:
    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_constitutive_goal_avoids_gal1(self, mock_search, mock_opt):
        result = introduce_gene(
            "GFP", "Aequorea victoria", "yeast",
            expression_goal="constitutive expression"
        )
        assert result["promoter"]["name"] != "GAL1", (
            "constitutive expression_goal must not select inducible GAL1"
        )

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_constitutive_goal_selects_constitutive_promoter(self, mock_search, mock_opt):
        result = introduce_gene(
            "GFP", "Aequorea victoria", "yeast",
            expression_goal="strong constitutive"
        )
        assert result["promoter"].get("expression_type") == "constitutive" or \
               result["promoter"].get("constitutive") is True

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_inducible_goal_selects_inducible_promoter(self, mock_search, mock_opt):
        result = introduce_gene(
            "GFP", "Aequorea victoria", "yeast",
            expression_goal="galactose inducible"
        )
        assert result["promoter"].get("expression_type") == "inducible" or \
               result["promoter"].get("inducible") is True

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_no_expression_goal_still_returns_a_promoter(self, mock_search, mock_opt):
        result = introduce_gene("GFP", "Aequorea victoria", "yeast")
        assert "name" in result["promoter"]


# ---------------------------------------------------------------------------
# _pick_backbone — backbone selection heuristics
# ---------------------------------------------------------------------------

_YEAST_BACKBONES = [
    {"name": "pRS316", "copy_number": "low", "ori": "CEN6/ARS4"},
    {"name": "pRS416", "copy_number": "high", "ori": "2-micron"},
    {"name": "pYES2",  "copy_number": "high", "ori": "2-micron", "promoter": "GAL1"},
    {"name": "pESC-HIS", "copy_number": "high", "ori": "2-micron", "promoter": "GAL1/GAL10 dual"},
]


class TestPickBackbone:
    def test_empty_list_returns_none(self):
        assert _pick_backbone([], "yeast", "inducible") is None

    def test_non_yeast_returns_first_regardless_of_expression_type(self):
        result = _pick_backbone(_YEAST_BACKBONES, "e_coli", "inducible")
        assert result["name"] == "pRS316"

    def test_none_expression_type_returns_first(self):
        result = _pick_backbone(_YEAST_BACKBONES, "yeast", None)
        assert result["name"] == "pRS316"

    def test_inducible_yeast_prefers_pyes2(self):
        result = _pick_backbone(_YEAST_BACKBONES, "yeast", "inducible")
        assert result["name"] == "pYES2"

    def test_inducible_yeast_falls_back_to_high_copy_when_no_pyes2(self):
        backbones_no_pyes2 = [
            {"name": "pRS316", "copy_number": "low"},
            {"name": "pRS416", "copy_number": "high"},
        ]
        result = _pick_backbone(backbones_no_pyes2, "yeast", "inducible")
        assert result["name"] == "pRS416"

    def test_constitutive_yeast_avoids_gal_promoter(self):
        result = _pick_backbone(_YEAST_BACKBONES, "yeast", "constitutive")
        # Should pick pRS416 (high-copy, no GAL promoter) over pYES2/pESC-HIS
        assert result["name"] == "pRS416"

    def test_constitutive_yeast_selects_high_copy(self):
        result = _pick_backbone(_YEAST_BACKBONES, "yeast", "constitutive")
        assert result.get("copy_number") == "high"

    def test_constitutive_falls_back_to_first_when_no_high_copy(self):
        backbones_low_only = [
            {"name": "pRS316", "copy_number": "low"},
            {"name": "pRS315", "copy_number": "low"},
        ]
        result = _pick_backbone(backbones_low_only, "yeast", "constitutive")
        assert result["name"] == "pRS316"


# ---------------------------------------------------------------------------
# introduce_gene — backbone selection driven by expression goal
# ---------------------------------------------------------------------------

class TestIntroduceGeneBackboneSelection:
    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_inducible_goal_selects_pyes2_for_yeast(self, mock_search, mock_opt):
        result = introduce_gene(
            "GFP", "Aequorea victoria", "yeast",
            expression_goal="galactose inducible",
        )
        assert result["vector"]["name"] == "pYES2", (
            f"Expected pYES2 for inducible yeast; got {result['vector']['name']}"
        )

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_constitutive_goal_avoids_pyes2_for_yeast(self, mock_search, mock_opt):
        result = introduce_gene(
            "GFP", "Aequorea victoria", "yeast",
            expression_goal="constitutive expression",
        )
        assert result["vector"]["name"] != "pYES2", (
            "Constitutive goal should not select pYES2 (GAL1-pre-loaded vector)"
        )


# ---------------------------------------------------------------------------
# Agrobacterium host path (Issue I fix)
# ---------------------------------------------------------------------------

class TestAgrobacteriumHost:
    """After Issue I fix, agrobacterium is a valid introduce_gene host."""

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_agrobacterium_host_accepted(self, mock_search, mock_opt):
        result = introduce_gene("nptII", "Agrobacterium tumefaciens", "agrobacterium")
        assert "error" not in result, f"agrobacterium host rejected: {result.get('error')}"

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_agrobacterium_returns_plant_binary_vector(self, mock_search, mock_opt):
        result = introduce_gene("nptII", "Agrobacterium tumefaciens", "agrobacterium")
        # Plant binary vectors: pCAMBIA1305.1, pCAMBIA1300, pBI121, pK2GW7
        expected_vectors = {"pCAMBIA1305.1", "pCAMBIA1300", "pBI121", "pK2GW7"}
        assert result["vector"]["name"] in expected_vectors, (
            f"Expected plant binary vector, got {result['vector']['name']}"
        )

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_agrobacterium_next_steps_mention_plant_infection(self, mock_search, mock_opt):
        result = introduce_gene("nptII", "Agrobacterium tumefaciens", "agrobacterium")
        steps_text = " ".join(result["next_steps"])
        # Protocol must include plant infection step
        assert any(kw in steps_text.lower() for kw in ("infect", "leaf", "infiltration", "t-dna")), (
            "Agrobacterium next steps must include plant infection / T-DNA step"
        )

    @patch("src.tools.gene_introduction.optimize_codons", side_effect=_fake_optimize_codons_ok)
    @patch("src.tools.gene_introduction.search_gene", side_effect=_fake_search_gene_ok)
    def test_agrobacterium_next_steps_mention_arabidopsis_codon_table(self, mock_search, mock_opt):
        result = introduce_gene("nptII", "Agrobacterium tumefaciens", "agrobacterium")
        steps_text = " ".join(result["next_steps"])
        assert "arabidopsis" in steps_text.lower(), (
            "Agrobacterium next steps must note Arabidopsis codon table usage"
        )


class TestBuildNextStepsPlant:
    def test_plant_nuclear_protocol_includes_t_dna(self):
        steps = _build_next_steps("plant_nuclear", "pCAMBIA1300", "HPT")
        steps_text = " ".join(steps).lower()
        assert "t-dna" in steps_text or "t_dna" in steps_text

    def test_agrobacterium_protocol_includes_regeneration(self):
        steps = _build_next_steps("agrobacterium", "pBI121", "NPTII")
        steps_text = " ".join(steps).lower()
        assert "regenerat" in steps_text  # "regenerate" or "regeneration"

    def test_agrobacterium_and_plant_nuclear_use_same_protocol(self):
        agro_steps = _build_next_steps("agrobacterium", "pBI121", "NPTII")
        plant_steps = _build_next_steps("plant_nuclear", "pBI121", "NPTII")
        assert agro_steps == plant_steps


# ---------------------------------------------------------------------------
# ATG start codon validation in optimize_codons
# ---------------------------------------------------------------------------

class TestOptimizeCodonsAtgValidation:
    def test_sequence_not_starting_with_atg_returns_error(self):
        from src.tools.sequence_design import optimize_codons
        result = optimize_codons("GCGGCGGCG", "e_coli")  # in-frame but no ATG
        assert "error" in result
        assert "ATG" in result["error"]

    def test_sequence_starting_with_atg_passes_validation(self):
        from src.tools.sequence_design import optimize_codons
        from unittest.mock import MagicMock, patch
        mock_instance = MagicMock()
        mock_instance.sequence = _GFP_CDS
        mock_module = MagicMock()
        mock_module.DnaOptimizationProblem.return_value = mock_instance
        mock_module.CodonOptimize.return_value = MagicMock()
        mock_module.EnforceTranslation.return_value = MagicMock()
        with patch.dict("sys.modules", {"dnachisel": mock_module}):
            result = optimize_codons(_GFP_CDS, "e_coli")
        assert "error" not in result

    def test_empty_sequence_returns_length_error(self):
        from src.tools.sequence_design import optimize_codons
        # Empty string: length 0, divisible by 3, but no ATG
        result = optimize_codons("", "e_coli")
        assert "error" in result
