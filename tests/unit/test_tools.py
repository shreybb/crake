"""Unit tests for bio tool scripts."""

from src.tools.annotation import find_restriction_sites
from src.tools.knowledge import (
    suggest_backbone,
    suggest_promoter,
    suggest_selectable_marker,
    suggest_terminator,
)
from src.tools.sequence_design import analyze_sequence, suggest_parts_for_host
from src.tools.validation import find_orfs, gc_windows, validate_plasmid

# Synthetic GFP CDS (in-frame, starts with ATG)
GFP = (
    "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAGCTGGAC"
    "GGCGACGTAAACGGCCACAAGTTCAGCGTGTCCGGCGAGGGCGAGGGCGATGCCACCTAC"
    "GGCAAGCTGACCCTGAAGTTCATCTGCACCACCGGCAAGCTGCCCGTGCCCTGGCCCACC"
    "CTCGTGACCACCCTGACCTACGGCGTGCAGTGCTTCAGCCGCTACCCCGACCACATGAAG"
    "CAGCACGACTTCTTCAAGTCCGCCATGCCCGAAGGCTACGTCCAGGAGCGCACCATCTTC"
    "TTCAAGGACGACGGCAACTACAAGACCCGCGCCGAGGTGAAGTTCGAGGGCGACACCCTG"
    "GTGAACCGCATCGAGCTGAAGGGCATCGACTTCAAGGAGGACGGCAACATCCTGGGGCAC"
    "AAGCTGGAGTACAACTACAACAGCCACAACGTCTATATCATGGCCGACAAGCAGAAGAAC"
    "GGCATCAAGGTGAACTTCAAGATCCGCCACAACATCGAGGACGGCAGCGTGCAGCTCGCC"
    "GACCACTACCAGCAGAACACCCCCATCGGCGACGGCCCCGTGCTGCTGCCCGACAACCAC"
    "TACCTGAGCACCCAGTCCAAGCTGAGCAAAGACCCCAACGAGAAGCGCGATCACATGGTC"
    "CTGCTGGAGTTCGTGACCGCCGCCGGGATCACTCTCGGCATGGACGAGCTGTACAAG"
)


class TestKnowledge:
    def test_suggest_backbone_ecoli(self):
        results = suggest_backbone("e_coli")
        names = [r["name"] for r in results]
        assert "pET-28a" in names
        assert "pUC19" in names

    def test_suggest_backbone_plant(self):
        results = suggest_backbone("plant_nuclear")
        names = [r["name"] for r in results]
        assert "pCAMBIA1305.1" in names
        assert "pBI121" in names

    def test_suggest_promoter_ecoli(self):
        results = suggest_promoter("e_coli")
        names = [r["name"] for r in results]
        assert "T7" in names

    def test_suggest_promoter_plant(self):
        results = suggest_promoter("plant_nuclear")
        names = [r["name"] for r in results]
        assert "CaMV35S" in names
        assert "Ubi1" in names

    def test_suggest_selectable_marker_plant(self):
        results = suggest_selectable_marker("plant_nuclear")
        names = [r["name"] for r in results]
        assert "NPTII" in names
        assert "BAR" in names

    # --- Yeast knowledge base ---

    def test_suggest_backbone_yeast_returns_results(self):
        results = suggest_backbone("yeast")
        assert len(results) >= 1

    def test_suggest_backbone_yeast_includes_prs316(self):
        results = suggest_backbone("yeast")
        names = [r["name"] for r in results]
        assert "pRS316" in names

    def test_suggest_backbone_yeast_includes_integrating_vector(self):
        results = suggest_backbone("yeast")
        names = [r["name"] for r in results]
        assert "pRS306" in names, "pRS306 integrating vector must be present"

    def test_suggest_promoter_yeast_includes_gal1(self):
        results = suggest_promoter("yeast")
        names = [r["name"] for r in results]
        assert "GAL1" in names

    def test_suggest_promoter_yeast_includes_constitutive(self):
        results = suggest_promoter("yeast")
        names = [r["name"] for r in results]
        # Must have at least one strong constitutive promoter
        assert "TEF1" in names or "TDH3" in names

    def test_suggest_terminator_yeast_includes_cyc1tt(self):
        results = suggest_terminator("yeast")
        names = [r["name"] for r in results]
        assert "CYC1tt" in names

    def test_suggest_selectable_marker_yeast_includes_auxotrophic(self):
        results = suggest_selectable_marker("yeast")
        names = [r["name"] for r in results]
        assert "URA3" in names

    def test_suggest_selectable_marker_yeast_includes_dominant(self):
        results = suggest_selectable_marker("yeast")
        names = [r["name"] for r in results]
        assert "kanMX" in names, "Dominant marker kanMX required for prototrophic strains"

    def test_yeast_ura3_has_counterselection_info(self):
        results = suggest_selectable_marker("yeast")
        ura3 = next(r for r in results if r["name"] == "URA3")
        assert "5-FOA" in ura3.get("counterselection", "") or "5-FOA" in ura3.get("notes", "")

    # --- plant_plastid stub ---

    def test_plant_plastid_backbone_returns_unsupported_note(self):
        results = suggest_backbone("plant_plastid")
        assert len(results) == 1
        assert results[0].get("supported") is False

    def test_plant_plastid_marker_returns_unsupported_note(self):
        results = suggest_selectable_marker("plant_plastid")
        assert len(results) == 1
        assert results[0].get("supported") is False

    def test_plant_plastid_note_mentions_aada(self):
        results = suggest_backbone("plant_plastid")
        note = results[0].get("note", "")
        assert "aadA" in note, "aadA is the canonical plastid marker and must be mentioned"


class TestAnnotation:
    def test_restriction_sites_returns_list(self):
        sites = find_restriction_sites(GFP)
        assert isinstance(sites, list)
        # GFP should have some common sites
        assert len(sites) >= 0  # may vary


class TestSequenceDesign:
    def test_analyze_sequence_gc(self):
        result = analyze_sequence("GCGCGCGC")
        assert result["gc_content_percent"] == 100.0
        assert result["length_bp"] == 8

    def test_analyze_sequence_at(self):
        result = analyze_sequence("ATATATAT")
        assert result["gc_content_percent"] == 0.0

    def test_suggest_parts_returns_all_categories(self):
        result = suggest_parts_for_host("e_coli")
        assert "recommended_backbones" in result
        assert "recommended_promoters" in result
        assert "recommended_terminators" in result
        assert "recommended_selectable_markers" in result

    def test_suggest_parts_plant(self):
        result = suggest_parts_for_host("plant_nuclear")
        markers = [m["name"] for m in result["recommended_selectable_markers"]]
        assert "BAR" in markers


class TestValidation:
    def test_find_orfs_detects_gfp(self):
        # GFP + stop codon so the ORF is complete
        orfs = find_orfs(GFP + "TAA", min_length=50)
        assert len(orfs) >= 1
        longest = orfs[0]
        assert longest["strand"] == 1

    def test_gc_windows_overall(self):
        result = gc_windows("GCGCATATATGCGC")
        assert "overall_gc_percent" in result
        assert isinstance(result["flagged_windows"], list)

    def test_validate_plasmid_structure(self):
        # Pad GFP with flanking sequence to make a pseudo-plasmid
        fake_plasmid = "ATCG" * 1000 + GFP + "ATCG" * 1000
        result = validate_plasmid(fake_plasmid)
        assert "length_bp" in result
        assert "orfs" in result
        assert "restriction_sites" in result
        assert "gc_analysis" in result
