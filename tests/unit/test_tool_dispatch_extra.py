"""Additional unit tests for agent tool_dispatch private helpers."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agent.tool_dispatch import _feat_color, _result_to_seqviz, _genbank_to_seqviz, dispatch


# ---------------------------------------------------------------------------
# _feat_color
# ---------------------------------------------------------------------------

class TestFeatColor:
    def test_known_type_returns_configured_color(self):
        color = _feat_color("CDS")
        assert color.startswith("#")

    def test_unknown_type_returns_default_color(self):
        color = _feat_color("weird_feature_type")
        assert color == "#818CF8"

    def test_cds_has_dedicated_color(self):
        # CDS is "#4ADE80", default is "#818CF8"
        color = _feat_color("CDS")
        default = _feat_color("nonexistent")
        assert color != default


# ---------------------------------------------------------------------------
# _result_to_seqviz
# ---------------------------------------------------------------------------

class TestResultToSeqviz:
    def test_returns_none_for_empty_sequence(self):
        result = _result_to_seqviz({"sequence": "", "gene_name": "test"})
        assert result is None

    def test_returns_none_for_protein_sequence(self):
        result = _result_to_seqviz({
            "sequence": "MVSK",
            "sequence_type": "protein",
            "gene_name": "GFP",
        })
        assert result is None

    def test_returns_dict_for_dna_sequence(self):
        result = _result_to_seqviz({
            "sequence": "ATCGATCG",
            "gene_name": "test_gene",
        })
        assert result is not None
        assert result["seq"] == "ATCGATCG"

    def test_name_truncated_to_30_chars(self):
        long_name = "A" * 50
        result = _result_to_seqviz({
            "sequence": "ATCGATCG",
            "gene_name": long_name,
        })
        assert len(result["name"]) <= 30

    def test_accession_used_when_no_gene_name(self):
        result = _result_to_seqviz({
            "sequence": "ATCGATCG",
            "accession": "ACC001",
        })
        assert result["name"] == "ACC001"

    def test_features_converted_to_annotations(self):
        result = _result_to_seqviz({
            "sequence": "ATCGATCGATCGATCG",
            "gene_name": "test",
            "features": [
                {
                    "type": "CDS",
                    "name": "gfp",
                    "start": 0,
                    "end": 12,
                    "strand": 1,
                },
            ],
        })
        assert len(result["annotations"]) == 1
        ann = result["annotations"][0]
        assert ann["start"] == 0
        assert ann["end"] == 12
        assert ann["direction"] == 1

    def test_feature_name_includes_type_prefix_when_different(self):
        result = _result_to_seqviz({
            "sequence": "ATCGATCGATCG",
            "gene_name": "test",
            "features": [
                {
                    "type": "promoter",
                    "name": "T7",
                    "start": 0,
                    "end": 6,
                    "strand": 1,
                },
            ],
        })
        ann = result["annotations"][0]
        assert "promoter" in ann["name"].lower()

    def test_feature_with_no_label_uses_type(self):
        result = _result_to_seqviz({
            "sequence": "ATCGATCG",
            "gene_name": "test",
            "features": [
                {
                    "type": "misc_feature",
                    "name": "",
                    "start": 0,
                    "end": 4,
                    "strand": 1,
                },
            ],
        })
        ann = result["annotations"][0]
        assert ann["name"] == "misc_feature"

    def test_empty_features_list(self):
        result = _result_to_seqviz({
            "sequence": "ATCGATCG",
            "gene_name": "test",
            "features": [],
        })
        assert result["annotations"] == []


# ---------------------------------------------------------------------------
# _genbank_to_seqviz
# ---------------------------------------------------------------------------

GENBANK_CONTENT = """\
LOCUS       pTest                     34 bp    DNA     circular SYN 01-JAN-2025
DEFINITION  Test plasmid.
ACCESSION   pTest
VERSION     pTest.1
KEYWORDS    .
SOURCE      synthetic construct
  ORGANISM  synthetic construct
            other sequences; artificial sequences.
FEATURES             Location/Qualifiers
     CDS             1..33
                     /gene="gfp"
     source          1..34
                     /organism="synthetic construct"
ORIGIN
        1 atggagctga acgatcgatc gatcgatcga tcg
//
"""


class TestGenBankToSeqviz:
    def test_returns_none_for_missing_file(self, tmp_path):
        result = _genbank_to_seqviz(tmp_path / "nonexistent.gb")
        assert result is None

    def test_returns_none_for_invalid_file(self, tmp_path):
        f = tmp_path / "bad.gb"
        f.write_text("not a genbank file")
        result = _genbank_to_seqviz(f)
        assert result is None

    def test_valid_genbank_returns_seqviz_dict(self, tmp_path):
        gb = tmp_path / "test.gb"
        gb.write_text(GENBANK_CONTENT)
        result = _genbank_to_seqviz(gb)
        assert result is not None
        assert "name" in result
        assert "seq" in result
        assert "annotations" in result

    def test_source_feature_excluded(self, tmp_path):
        gb = tmp_path / "test.gb"
        gb.write_text(GENBANK_CONTENT)
        result = _genbank_to_seqviz(gb)
        # source feature should be skipped
        ann_names = [a["name"] for a in result["annotations"]]
        assert not any("source" in n.lower() for n in ann_names)

    def test_annotations_have_required_keys(self, tmp_path):
        gb = tmp_path / "test.gb"
        gb.write_text(GENBANK_CONTENT)
        result = _genbank_to_seqviz(gb)
        for ann in result["annotations"]:
            assert "name" in ann
            assert "start" in ann
            assert "end" in ann
            assert "color" in ann


# ---------------------------------------------------------------------------
# dispatch — import_sequence and unknown method paths
# ---------------------------------------------------------------------------

class TestDispatchImportSequence:
    def test_import_sequence_success_updates_session(self, tmp_path):
        fa = tmp_path / "seq.fa"
        fa.write_text(">test\nATCGATCGATCGATCG\n")
        session: dict = {}
        result = dispatch("import_sequence", {"path": str(fa)}, session)
        assert "sequence" in result
        assert session.get("last_sequence") is not None

    def test_import_sequence_error_does_not_update_session(self, tmp_path):
        session: dict = {}
        result = dispatch("import_sequence", {"path": str(tmp_path / "missing.gb")}, session)
        assert "error" in result
        assert "last_sequence" not in session


class TestDispatchFindTargetSitesUnknownMethod:
    def test_unknown_method_returns_error(self):
        session: dict = {}
        result = dispatch("find_target_sites", {
            "sequence": "ATCGATCGATCG",
            "method": "nonexistent_method",
        }, session)
        assert "error" in result


class TestSearchGeneException:
    """Cover the exception branch in search_gene (lines 142-143)."""

    def test_esearch_exception_returns_error(self):
        from src.tools.fetch_sequence import search_gene
        from unittest.mock import patch

        with patch(
            "src.tools.fetch_sequence.Entrez.esearch",
            side_effect=Exception("network error"),
        ):
            result = search_gene("GFP", "E. coli")
        assert "error" in result
        assert result.get("gene") == "GFP"


# ---------------------------------------------------------------------------
# validate_plasmid topology wiring
# ---------------------------------------------------------------------------

class TestValidatePlasmidTopology:
    def test_default_topology_is_circular(self):
        seq = "ATCG" * 100
        session: dict = {}
        result = dispatch("validate_plasmid", {"sequence": seq}, session)
        assert result["topology"] == "circular"

    def test_linear_topology_is_passed_through(self):
        seq = "ATCG" * 100
        session: dict = {}
        result = dispatch("validate_plasmid", {
            "sequence": seq,
            "topology": "linear",
        }, session)
        assert result["topology"] == "linear"

    def test_topology_stored_in_last_validation(self):
        seq = "ATCG" * 100
        session: dict = {}
        dispatch("validate_plasmid", {"sequence": seq, "topology": "linear"}, session)
        assert session["last_validation"]["topology"] == "linear"


# ---------------------------------------------------------------------------
# gene_introduction yeast next steps
# ---------------------------------------------------------------------------

class TestIntroduceGeneYeastNextSteps:
    def test_yeast_ura3_next_steps_mention_strain_auxotrophy(self):
        from src.tools.gene_introduction import _build_next_steps
        steps = _build_next_steps("yeast", "pRS316", "URA3")
        combined = " ".join(steps)
        assert "ura3" in combined.lower(), "URA3 steps must specify ura3Δ strain requirement"

    def test_yeast_next_steps_mention_lithium_acetate(self):
        from src.tools.gene_introduction import _build_next_steps
        steps = _build_next_steps("yeast", "pRS316", "URA3")
        combined = " ".join(steps)
        assert "lithium acetate" in combined.lower() or "liac" in combined.lower()

    def test_yeast_gal1_next_steps_mention_galactose_induction(self):
        from src.tools.gene_introduction import _build_next_steps
        steps = _build_next_steps("yeast", "pYES2", "URA3")
        combined = " ".join(steps)
        assert "galactose" in combined.lower()

    def test_yeast_dominant_marker_next_steps_mention_any_strain(self):
        from src.tools.gene_introduction import _build_next_steps
        steps = _build_next_steps("yeast", "pRS316", "kanMX")
        combined = " ".join(steps)
        assert "any strain" in combined.lower() or "g418" in combined.lower()

    def test_ecoli_next_steps_unchanged(self):
        from src.tools.gene_introduction import _build_next_steps
        steps = _build_next_steps("e_coli", "pET-28a", "KanR")
        assert len(steps) == 6
        assert "lithium" not in " ".join(steps).lower()
