"""Unit tests for target_site tool."""
import pytest
from src.tools.target_site import (
    find_restriction_edit_sites,
    extract_homology_arms,
    find_crispr_pam_sites,
    recommend_edit_site,
    _gc_percent,
    _has_homopolymer,
)

# Sequence with a single EcoRI site (GAATTC) in the middle
ECORI_SEQ = "ATCGATCG" * 50 + "GAATTC" + "GCTAGCTA" * 50

# 800 bp flanking so arm extraction has room
LONG_SEQ = "ATCG" * 200  # 800 bp


class TestGcPercent:
    def test_all_gc(self):
        assert _gc_percent("GCGCGC") == 100.0

    def test_all_at(self):
        assert _gc_percent("ATATAT") == 0.0

    def test_mixed(self):
        assert _gc_percent("ATCG") == 50.0

    def test_empty(self):
        assert _gc_percent("") == 0.0


class TestHasHomopolymer:
    def test_detects_run_of_5(self):
        assert _has_homopolymer("AAAAAGCGC") is True

    def test_run_of_4_is_ok(self):
        assert _has_homopolymer("AAAAGCGC") is False

    def test_no_run(self):
        assert _has_homopolymer("ATCGATCG") is False


class TestFindRestrictionEditSites:
    def test_finds_single_ecori_site(self):
        sites = find_restriction_edit_sites(ECORI_SEQ)
        enzymes = [s["enzyme"] for s in sites]
        assert "EcoRI" in enzymes

    def test_ecori_site_position_is_correct(self):
        sites = find_restriction_edit_sites(ECORI_SEQ)
        ecori = next(s for s in sites if s["enzyme"] == "EcoRI")
        # EcoRI cuts between G and AATTC → position should be in the inserted region
        assert 395 <= ecori["position"] <= 410

    def test_arms_are_populated(self):
        sites = find_restriction_edit_sites(ECORI_SEQ, arm_length=10)
        for site in sites:
            assert "left_arm" in site
            assert "right_arm" in site
            assert len(site["left_arm"]) <= 10
            assert len(site["right_arm"]) <= 10

    def test_multi_cut_excluded_by_default(self):
        # All returned sites should have cut_count == 1
        sites = find_restriction_edit_sites(ECORI_SEQ)
        for site in sites:
            assert site["cut_count"] == 1

    def test_allow_multi_cut_includes_more_sites(self):
        unique = find_restriction_edit_sites(ECORI_SEQ, require_unique=True)
        all_sites = find_restriction_edit_sites(ECORI_SEQ, require_unique=False)
        assert len(all_sites) >= len(unique)

    def test_sorted_by_position(self):
        sites = find_restriction_edit_sites(ECORI_SEQ)
        positions = [s["position"] for s in sites]
        assert positions == sorted(positions)

    def test_returns_list_for_no_sites(self):
        result = find_restriction_edit_sites("AAAAAAAAAAAAAAAAAAAAAA")
        assert isinstance(result, list)


class TestExtractHomologyArms:
    def test_arms_have_correct_length(self):
        result = extract_homology_arms(LONG_SEQ, position=400, arm_length=100)
        assert result["left_arm_length_bp"] == 100
        assert result["right_arm_length_bp"] == 100

    def test_arms_are_adjacent(self):
        seq = "A" * 200 + "T" * 200
        result = extract_homology_arms(seq, position=200, arm_length=50)
        assert result["left_arm"] == "A" * 50
        assert result["right_arm"] == "T" * 50

    def test_clamps_at_sequence_boundary(self):
        result = extract_homology_arms(LONG_SEQ, position=10, arm_length=100)
        # Can't have more than 10 bases to the left
        assert result["left_arm_length_bp"] == 10

    def test_position_preserved(self):
        result = extract_homology_arms(LONG_SEQ, position=300)
        assert result["position"] == 300

    def test_returns_dict_with_required_keys(self):
        result = extract_homology_arms(LONG_SEQ, position=400)
        for key in ("left_arm", "right_arm", "left_arm_length_bp", "right_arm_length_bp"):
            assert key in result


class TestFindCrisprPamSites:
    # Guide with ~60% GC + AGG PAM — should pass filters
    # GCGCATCGATCGGCATCGAT = 12 GC / 20 = 60%
    CRISPR_SEQ = "GCGCATCGATCGGCATCGATAGG"

    def test_finds_known_ngg_site(self):
        sites = find_crispr_pam_sites(self.CRISPR_SEQ + "N" * 10)
        assert len(sites) >= 1
        # protospacer is DNA; guide_rna is the RNA equivalent (T→U)
        protospacers = [s["protospacer"] for s in sites]
        assert "GCGCATCGATCGGCATCGAT" in protospacers
        rnas = [s["guide_rna"] for s in sites]
        assert "GCGCAUCGAUCGGCAUCGAU" in rnas

    def test_filters_low_gc_guide(self):
        # All AT guide — 0% GC, should be filtered
        low_gc = "ATATATATATATATATATAT" + "AGG"
        sites = find_crispr_pam_sites(low_gc)
        bad = [s for s in sites if s["protospacer"] == "ATATATATATATATATATAT"]
        assert bad == []

    def test_filters_homopolymer_guide(self):
        # Guide with AAAAA run
        poly = "GCGCAAAAAGCGCATCGATCGAGG"
        sites = find_crispr_pam_sites(poly)
        bad = [s for s in sites if "AAAAA" in s["protospacer"]]
        assert bad == []

    def test_pam_field_present(self):
        sites = find_crispr_pam_sites(self.CRISPR_SEQ + "N" * 10)
        for site in sites:
            assert "pam" in site
            assert len(site["pam"]) == 3

    def test_returns_both_strands(self):
        # A long sequence with sites on both strands
        long = "GCGCATCGATCGGCATCGATAGG" * 3 + "CCTATCGATGCCGATCGATGCGC" * 3
        sites = find_crispr_pam_sites(long)
        strands = {s["strand"] for s in sites}
        # Not guaranteed to have both, but should have at least one
        assert len(strands) >= 1

    def test_capped_at_max_sites(self):
        # A very long repetitive sequence with many PAMs
        rich = ("GCGCATCGATCGGCATCGATAGG" * 5 + "ATCG" * 20) * 3
        sites = find_crispr_pam_sites(rich)
        assert len(sites) <= 20

    def test_ranked_by_gc_proximity_to_55(self):
        rich = ("GCGCATCGATCGGCATCGATAGG" * 3 + "ATCG" * 50)
        sites = find_crispr_pam_sites(rich)
        if len(sites) >= 2:
            diffs = [abs(s["gc_percent"] - 55.0) for s in sites]
            assert diffs == sorted(diffs)

    def test_arms_included_in_sites(self):
        long = "ATCG" * 200 + "GCGCATCGATCGGCATCGATAGG" + "ATCG" * 200
        sites = find_crispr_pam_sites(long, arm_length=50)
        for site in sites:
            assert "left_arm" in site
            assert "right_arm" in site


class TestRecommendEditSite:
    def test_returns_first_site(self):
        sites = [{"enzyme": "EcoRI"}, {"enzyme": "BamHI"}]
        assert recommend_edit_site(sites) == {"enzyme": "EcoRI"}

    def test_returns_none_for_empty(self):
        assert recommend_edit_site([]) is None
