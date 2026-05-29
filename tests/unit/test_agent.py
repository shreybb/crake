"""Unit tests for tool_dispatch (no Streamlit, no network)."""
from __future__ import annotations

import pytest

from src.agent.tool_dispatch import dispatch


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

    def test_fetch_uniprot_routes_to_uniprot_helper(self, mocker):
        mock_fn = mocker.patch(
            "src.agent.tool_dispatch._fetch_from_uniprot",
            return_value={"sequence": "MV", "sequence_type": "protein"},
        )
        dispatch("fetch_by_accession", {"accession": "P42212", "db": "uniprot"}, {})
        mock_fn.assert_called_once_with("P42212")

    def test_optimize_codons_passes_sequence_and_host(self, mocker):
        mock_fn = mocker.patch(
            "src.agent.tool_dispatch._optimize_codons",
            return_value={"optimized_sequence": "ATG"},
        )
        dispatch("optimize_codons", {"sequence": "ATGATG", "host": "plant_nuclear"}, {})
        mock_fn.assert_called_once_with("ATGATG", "plant_nuclear")

    def test_optimize_codons_updates_last_sequence_on_success(self, mocker):
        mocker.patch(
            "src.agent.tool_dispatch._optimize_codons",
            return_value={
                "optimized_sequence": "ATGCCC",
                "gc_before": 50.0,
                "gc_after": 48.0,
            },
        )
        session = {
            "last_sequence": {
                "gene_name": "GFP",
                "sequence": "ATGAAA",
                "organism": "test",
                "topology": "linear",
            }
        }
        dispatch("optimize_codons", {"sequence": "ATGAAA", "host": "e_coli"}, session)
        assert session["last_sequence"]["sequence"] == "ATGCCC"
        assert session["last_sequence"]["gene_name"] == "GFP"
        assert session["last_seqviz"] is not None
        assert session["last_seqviz"]["seq"] == "ATGCCC"

    def test_optimize_codons_error_leaves_last_sequence_unchanged(self, mocker):
        mocker.patch(
            "src.agent.tool_dispatch._optimize_codons",
            return_value={"error": "failed", "original_sequence": "ATGAAA"},
        )
        session = {"last_sequence": {"sequence": "ATGAAA", "gene_name": "GFP"}}
        dispatch("optimize_codons", {"sequence": "ATGAAA", "host": "e_coli"}, session)
        assert session["last_sequence"]["sequence"] == "ATGAAA"

    def test_suggest_parts_passes_host(self, mocker):
        mock_fn = mocker.patch(
            "src.agent.tool_dispatch._suggest_parts",
            return_value={"recommended_backbones": []},
        )
        dispatch("suggest_parts", {"host": "agrobacterium"}, {})
        mock_fn.assert_called_once_with("agrobacterium")

    def test_failed_assembly_does_not_overwrite_last_assembly(self, mocker):
        mocker.patch(
            "src.agent.tool_dispatch.simulate_gibson",
            return_value={"success": False, "error": "no overlap"},
        )
        session = {
            "last_assembly": {
                "success": True,
                "product_sequence": "ATCGATCG",
                "topology": "circular",
            }
        }
        dispatch("simulate_assembly", {"fragments": ["A", "B"], "method": "gibson"}, session)
        assert session["last_assembly"]["product_sequence"] == "ATCGATCG"

    def test_successful_assembly_updates_last_assembly(self, mocker):
        mocker.patch(
            "src.agent.tool_dispatch.simulate_gibson",
            return_value={
                "success": True,
                "product_sequence": "NEWSEQ",
                "topology": "circular",
            },
        )
        session = {
            "last_assembly": {
                "success": True,
                "product_sequence": "OLDSEQ",
            }
        }
        dispatch("simulate_assembly", {"fragments": ["A", "B"], "method": "gibson"}, session)
        assert session["last_assembly"]["product_sequence"] == "NEWSEQ"

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
        mocker.patch(
            "src.agent.tool_dispatch.find_restriction_edit_sites",
            return_value=[{"enzyme": "EcoRI", "position": 100}],
        )
        result = dispatch("find_target_sites", {"sequence": "ATCG", "method": "restriction"}, {})
        assert result["method"] == "restriction"
        assert result["site_count"] == 1

    def test_find_target_sites_crispr_method(self, mocker):
        mocker.patch(
            "src.agent.tool_dispatch.find_crispr_pam_sites",
            return_value=[{"guide_rna": "GCGCATCGATCGATCGATCG"}],
        )
        result = dispatch("find_target_sites", {"sequence": "ATCG" * 50, "method": "crispr"}, {})
        assert result["method"] == "crispr"

    def test_find_target_sites_homologous_method(self, mocker):
        mocker.patch(
            "src.agent.tool_dispatch.extract_homology_arms",
            return_value={"left_arm": "AAAA", "right_arm": "TTTT", "position": 200},
        )
        result = dispatch(
            "find_target_sites",
            {"sequence": "ATCG" * 100, "method": "homologous", "position": 200},
            {},
        )
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
            return_value={"passed_checks": True, "warnings": []},
        )
        session = {}
        dispatch("validate_plasmid", {"sequence": "ATCG" * 100}, session)
        assert session["last_validation"]["passed_checks"] is True

    def test_export_reads_from_session(self, mocker, tmp_path):
        session = {
            "last_assembly": {
                "product_sequence": "ATCGATCG" * 100,
                "topology": "circular",
                "method": "gibson",
                "input_parts": [],
            },
            "last_validation": {
                "orfs": [],
                "restriction_sites": [],
                "warnings": [],
                "gc_analysis": {"overall_gc_percent": 50, "flagged_windows": []},
            },
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
