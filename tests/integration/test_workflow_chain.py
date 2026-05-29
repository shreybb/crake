"""Integration test: dispatch session chain without network.

import → optimize → validate → primers → gibson → export
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.agent.tool_dispatch import dispatch
from tests.unit.test_assembly import FRAG_A, FRAG_B

# Valid CDS for codon optimization (length divisible by 3, starts with ATG).
_CDS = (
    "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAGCTGGAC"
    "GGCGACGTAAACGGCCACAAGTTCAGCGTGTCCGGCGAGGGCGAGGGCGATGCCACCTAC"
    "GGCAAGCTGACCCTGAAGTTCATCTGCACCACCGGCAAGCTGCCCGTGCCCTGGCCCACC"
    "CTCGTGACCACCCTGACCTACGGCGTGCAGTGCTTCAGCCGCTACCCCGACCACATGAAG"
    "CAGCACGACTTCTTCAAGTCCGCCATGCCCGAAGGCTACGTCCAGGAGCGCACCATCTTCT"
    "TCAAGATCCGCCACAACATCGAGGACGGCAGCGTGCAGCTCGCCGGCCACCTCGCCCTCAA"
    "CTTCGAGATCAGCGAGTTCATCTACAAGGCTAAGATCCGCGAGCACAATCTGCTGGAGTA"
    "CAACTTCAACAGCCACAATGTGTACATCACGGCCGACAAGCAGAAGAACGGCATCAAGGT"
    "GAACTTCAAGATCCGCCACAACATCGAGGACGGCAGCGTGCAGCTCGCCGGCCACTAA"
)


def _mock_gibson_success():
    product_seq = FRAG_A + FRAG_B
    mock_product = MagicMock()
    mock_product.seq = MagicMock()
    mock_product.seq.__str__ = lambda s: product_seq
    mock_product.__len__ = lambda s: len(product_seq)

    mock_assembly = MagicMock()
    mock_assembly.assemble_circular.return_value = [mock_product]
    return patch("src.tools.assembly.Assembly", return_value=mock_assembly)


class TestWorkflowChain:
    def test_import_optimize_validate_primers_assemble_export(self, tmp_path):
        session: dict = {}
        fa = tmp_path / "gene.fa"
        fa.write_text(f">GFP\n{_CDS}\n")

        imp = dispatch("import_sequence", {"path": str(fa)}, session)
        assert "error" not in imp
        imported = session["last_sequence"]["sequence"]
        assert len(imported) > 0

        opt = dispatch(
            "optimize_codons",
            {"sequence": session["last_sequence"]["sequence"], "host": "e_coli"},
            session,
        )
        assert "error" not in opt
        assert session["last_sequence"]["sequence"] == opt["optimized_sequence"]
        assert session["last_sequence"]["sequence"] != imported
        assert session["last_seqviz"]["seq"] == opt["optimized_sequence"]

        opt_seq = session["last_sequence"]["sequence"]

        val = dispatch(
            "validate_plasmid",
            {"sequence": opt_seq, "topology": "linear", "name": "chain_test"},
            session,
        )
        assert "error" not in val
        assert session["last_validation"]["length_bp"] == len(opt_seq)

        prim = dispatch("design_primers", {"template": opt_seq}, session)
        assert "error" not in prim
        assert session["last_primers"].get("primer_pairs")

        frag_a = tmp_path / "insert.fa"
        frag_b = tmp_path / "backbone.fa"
        frag_a.write_text(f">insert\n{FRAG_A}\n")
        frag_b.write_text(f">backbone\n{FRAG_B}\n")

        with _mock_gibson_success():
            asm = dispatch(
                "simulate_assembly",
                {"method": "gibson", "fragments": [str(frag_a), str(frag_b)]},
                session,
            )
        assert asm["success"] is True
        assert session["last_assembly"]["product_sequence"]
        assert session["last_assembly"].get("provenance") == "simulated"

        out_dir = tmp_path / "export"
        paths = dispatch(
            "export_files",
            {"name": "pChain", "output_dir": str(out_dir)},
            session,
        )
        assert paths.get("provenance") == "simulated"
        assert Path(paths["genbank"]).is_file()
        assert Path(paths["fasta"]).is_file()
        assert Path(paths["protocol"]).is_file()
        assert session["export_paths"] == paths
