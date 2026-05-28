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
LOCUS       pTest                     33 bp    DNA     circular SYN 01-JAN-2025
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
     source          1..33
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


# ---------------------------------------------------------------------------
# Tool definition schema — enum consistency (Issues K and L)
# ---------------------------------------------------------------------------

class TestToolDefinitionsEnums:
    """Tool schemas must stay in sync with what the Python handlers accept."""

    def _get_tool(self, name: str) -> dict:
        from src.agent.tool_definitions import TOOL_DEFINITIONS
        for t in TOOL_DEFINITIONS:
            if t["name"] == name:
                return t
        raise KeyError(f"Tool '{name}' not found in TOOL_DEFINITIONS")

    def test_introduce_gene_target_host_includes_agrobacterium(self):
        """Issue K fix: agrobacterium must be in introduce_gene.target_host enum."""
        tool = self._get_tool("introduce_gene")
        enum = tool["input_schema"]["properties"]["target_host"]["enum"]
        assert "agrobacterium" in enum, (
            f"agrobacterium missing from introduce_gene.target_host enum: {enum}"
        )

    def test_introduce_gene_target_host_enum_matches_valid_hosts(self):
        """introduce_gene schema enum must match _VALID_HOSTS in the Python function."""
        from src.tools.gene_introduction import _VALID_HOSTS
        tool = self._get_tool("introduce_gene")
        enum_set = set(tool["input_schema"]["properties"]["target_host"]["enum"])
        assert enum_set == _VALID_HOSTS, (
            f"Schema enum {enum_set} does not match _VALID_HOSTS {_VALID_HOSTS}"
        )

    def test_find_target_sites_has_topology_parameter(self):
        """Issue L fix: topology must be exposed in find_target_sites tool schema."""
        tool = self._get_tool("find_target_sites")
        assert "topology" in tool["input_schema"]["properties"], (
            "topology parameter missing from find_target_sites tool definition"
        )

    def test_find_target_sites_topology_enum(self):
        """topology must accept 'linear' and 'circular'."""
        tool = self._get_tool("find_target_sites")
        enum = tool["input_schema"]["properties"]["topology"]["enum"]
        assert "linear" in enum
        assert "circular" in enum

    def test_suggest_parts_host_includes_agrobacterium(self):
        """suggest_parts already had agrobacterium — verify it hasn't regressed."""
        tool = self._get_tool("suggest_parts")
        enum = tool["input_schema"]["properties"]["host"]["enum"]
        assert "agrobacterium" in enum


class TestDispatchFindTargetSitesTopology:
    """Verify topology is forwarded to find_restriction_edit_sites (Issue L fix)."""

    def test_circular_topology_forwarded_to_restriction_method(self):
        from unittest.mock import patch, MagicMock
        with patch("src.agent.tool_dispatch.find_restriction_edit_sites") as mock_fn:
            mock_fn.return_value = []
            dispatch("find_target_sites", {
                "sequence": "ATCGATCGATCGATCGATCG",
                "method": "restriction",
                "topology": "circular",
            }, {})
            _, kwargs = mock_fn.call_args
            assert kwargs.get("topology") == "circular"

    def test_linear_topology_forwarded_to_restriction_method(self):
        from unittest.mock import patch
        with patch("src.agent.tool_dispatch.find_restriction_edit_sites") as mock_fn:
            mock_fn.return_value = []
            dispatch("find_target_sites", {
                "sequence": "ATCGATCGATCGATCGATCG",
                "method": "restriction",
                "topology": "linear",
            }, {})
            _, kwargs = mock_fn.call_args
            assert kwargs.get("topology") == "linear"

    def test_topology_defaults_to_linear_when_not_provided(self):
        from unittest.mock import patch
        with patch("src.agent.tool_dispatch.find_restriction_edit_sites") as mock_fn:
            mock_fn.return_value = []
            dispatch("find_target_sites", {
                "sequence": "ATCGATCGATCGATCGATCG",
                "method": "restriction",
            }, {})
            _, kwargs = mock_fn.call_args
            assert kwargs.get("topology") == "linear"


class TestDispatchCrisprPamForwarding:
    """Issue V fix: pam parameter must be forwarded to find_crispr_pam_sites.

    SpCas9 (NGG) is the default, but researchers targeting AT-rich plant genomes
    may need Cas12a (TTTV) or SaCas9 (NNGRRT) — both already supported by
    find_crispr_pam_sites() but previously unreachable through the agent tool.
    """

    def test_default_pam_is_ngg(self):
        from unittest.mock import patch
        with patch("src.agent.tool_dispatch.find_crispr_pam_sites") as mock_fn:
            mock_fn.return_value = []
            result = dispatch("find_target_sites", {
                "sequence": "ATCGATCGATCGATCGATCG",
                "method": "crispr",
            }, {})
            _, kwargs = mock_fn.call_args
            assert kwargs.get("pam") == "NGG", "Default PAM must be NGG (SpCas9)"

    def test_custom_pam_forwarded(self):
        """Cas12a TTTV PAM must reach find_crispr_pam_sites."""
        from unittest.mock import patch
        with patch("src.agent.tool_dispatch.find_crispr_pam_sites") as mock_fn:
            mock_fn.return_value = []
            dispatch("find_target_sites", {
                "sequence": "ATCGATCGATCGATCGATCG",
                "method": "crispr",
                "pam": "TTTV",
            }, {})
            _, kwargs = mock_fn.call_args
            assert kwargs.get("pam") == "TTTV", (
                "Cas12a PAM 'TTTV' was not forwarded to find_crispr_pam_sites"
            )

    def test_pam_returned_in_result(self):
        """Result dict must include the pam that was used."""
        from unittest.mock import patch
        with patch("src.agent.tool_dispatch.find_crispr_pam_sites") as mock_fn:
            mock_fn.return_value = []
            result = dispatch("find_target_sites", {
                "sequence": "ATCGATCGATCGATCGATCG",
                "method": "crispr",
                "pam": "NNGRRT",
            }, {})
            assert result.get("pam") == "NNGRRT", (
                "Result should echo back the pam used so the caller knows which nuclease was scanned"
            )

    def test_pam_schema_has_ngg_default(self):
        """Tool schema must have pam property with NGG as default."""
        from src.agent.tool_definitions import TOOL_DEFINITIONS
        tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "find_target_sites")
        pam_schema = tool["input_schema"]["properties"].get("pam")
        assert pam_schema is not None, "pam property missing from find_target_sites schema"
        assert pam_schema.get("default") == "NGG"

    def test_pam_schema_description_mentions_cas12a(self):
        """Description must mention Cas12a so researchers know they can use it."""
        from src.agent.tool_definitions import TOOL_DEFINITIONS
        tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "find_target_sites")
        desc = tool["input_schema"]["properties"]["pam"]["description"]
        assert "Cas12a" in desc or "TTTV" in desc, (
            "pam description should mention Cas12a/TTTV for AT-rich genome users"
        )
