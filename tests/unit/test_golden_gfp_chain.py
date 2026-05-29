"""Golden regression: optimize → validate → primers on fixed GFP CDS."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.agent.tool_dispatch import dispatch

_GOLDEN_DIR = Path(__file__).parent / "golden_fixtures"
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


def _normalize(result: dict) -> dict:
    out = dict(result)
    if "optimized_sequence" in out and isinstance(out["optimized_sequence"], str):
        out["optimized_sequence"] = f"<seq len={len(out['optimized_sequence'])}>"
    if "primer_pairs" in out:
        out["primer_pairs"] = [
            {
                "rank": p.get("rank"),
                "forward_len": len(p.get("forward", {}).get("binding_region", "")),
                "reverse_len": len(p.get("reverse", {}).get("binding_region", "")),
            }
            for p in out.get("primer_pairs", [])[:3]
        ]
    return out


@pytest.fixture
def session_with_cds(tmp_path):
    session: dict = {}
    fa = tmp_path / "gfp.fa"
    fa.write_text(f">GFP\n{_CDS}\n")
    dispatch("import_sequence", {"path": str(fa)}, session)
    return session


class TestGfpGolden:
    def test_optimize_validate_primers_snapshot(self, session_with_cds):
        session = session_with_cds
        seq = session["last_sequence"]["sequence"]
        opt = dispatch(
            "optimize_codons",
            {"sequence": seq, "host": "e_coli"},
            session,
        )
        opt_seq = session["last_sequence"]["sequence"]
        val = dispatch(
            "validate_plasmid",
            {"sequence": opt_seq, "name": "gfp", "topology": "linear"},
            session,
        )
        prim = dispatch("design_primers", {"template": opt_seq}, session)

        snapshot = {
            "optimize": _normalize(opt),
            "validate_keys": sorted(val.keys()),
            "validate_passed": val.get("passed_checks"),
            "validate_length": val.get("length_bp"),
            "primers": _normalize(prim),
        }

        golden_path = _GOLDEN_DIR / "gfp_e_coli_chain.json"
        if os.environ.get("CRAKE_UPDATE_GOLDEN"):
            golden_path.parent.mkdir(parents=True, exist_ok=True)
            golden_path.write_text(json.dumps(snapshot, indent=2) + "\n")
            pytest.skip("golden updated")

        if not golden_path.exists():
            pytest.skip("golden fixture missing — run with CRAKE_UPDATE_GOLDEN=1")

        expected = json.loads(golden_path.read_text())
        assert snapshot == expected
