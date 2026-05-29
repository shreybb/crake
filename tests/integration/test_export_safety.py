"""Integration tests for export provenance and session chain."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.agent.tool_dispatch import dispatch

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


class TestExportSafety:
    def test_export_without_assembly_raises(self, tmp_path):
        session: dict = {}
        fa = tmp_path / "gene.fa"
        fa.write_text(f">GFP\n{_CDS}\n")
        dispatch("import_sequence", {"path": str(fa)}, session)
        dispatch(
            "validate_plasmid",
            {
                "sequence": session["last_sequence"]["sequence"],
                "name": "t",
                "topology": "linear",
            },
            session,
        )
        with pytest.raises(ValueError, match="Assembly has not been simulated"):
            dispatch(
                "export_files",
                {"name": "pOnly", "output_dir": str(tmp_path / "out")},
                session,
            )

    def test_export_sequence_only_allowed(self, tmp_path):
        session: dict = {}
        fa = tmp_path / "gene.fa"
        fa.write_text(f">GFP\n{_CDS}\n")
        dispatch("import_sequence", {"path": str(fa)}, session)
        out_dir = tmp_path / "out"
        paths = dispatch(
            "export_files",
            {
                "name": "pOnly",
                "output_dir": str(out_dir),
                "allow_sequence_only": True,
            },
            session,
        )
        assert paths.get("provenance") == "not_run"
        assert Path(paths["protocol"]).is_file()
        assert "not simulated" in Path(paths["protocol"]).read_text().lower()

    def test_optimize_promotes_sequence(self, tmp_path):
        session: dict = {}
        fa = tmp_path / "gene.fa"
        fa.write_text(f">GFP\n{_CDS}\n")
        dispatch("import_sequence", {"path": str(fa)}, session)
        imported = session["last_sequence"]["sequence"]
        opt = dispatch(
            "optimize_codons",
            {"sequence": imported, "host": "e_coli"},
            session,
        )
        assert "error" not in opt
        assert session["last_sequence"]["sequence"] == opt["optimized_sequence"]
        assert session["last_sequence"]["sequence"] != imported
