"""Additional unit tests for annotation tool (annotate_from_genbank)."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.tools.annotation import annotate_from_genbank, find_restriction_sites


GENBANK_CONTENT = """\
LOCUS       pTest                     34 bp    DNA     circular SYN 01-JAN-2025
DEFINITION  Test circular plasmid.
ACCESSION   pTest
VERSION     pTest.1
KEYWORDS    .
SOURCE      synthetic construct
  ORGANISM  synthetic construct
            other sequences; artificial sequences; vectors.
FEATURES             Location/Qualifiers
     CDS             1..33
                     /gene="gfp"
                     /note="green fluorescent protein"
     promoter        complement(1..10)
                     /label="T7"
ORIGIN
        1 atggagctga acgatcgatc gatcgatcga tcg
//
"""


class TestAnnotateFromGenbank:
    def test_returns_name_and_description(self, tmp_path):
        gb = tmp_path / "seq.gb"
        gb.write_text(GENBANK_CONTENT)
        result = annotate_from_genbank(str(gb))
        assert result["name"] == "pTest"
        assert "description" in result

    def test_returns_length(self, tmp_path):
        gb = tmp_path / "seq.gb"
        gb.write_text(GENBANK_CONTENT)
        result = annotate_from_genbank(str(gb))
        # The GENBANK_CONTENT ORIGIN has 33 actual bases (Biopython reads what's there)
        assert result["length"] in (33, 34)

    def test_returns_topology(self, tmp_path):
        gb = tmp_path / "seq.gb"
        gb.write_text(GENBANK_CONTENT)
        result = annotate_from_genbank(str(gb))
        assert result["topology"] == "circular"

    def test_features_list_present(self, tmp_path):
        gb = tmp_path / "seq.gb"
        gb.write_text(GENBANK_CONTENT)
        result = annotate_from_genbank(str(gb))
        assert isinstance(result["features"], list)
        assert len(result["features"]) >= 1

    def test_feature_has_required_keys(self, tmp_path):
        gb = tmp_path / "seq.gb"
        gb.write_text(GENBANK_CONTENT)
        result = annotate_from_genbank(str(gb))
        feat = result["features"][0]
        for key in ("type", "location", "start", "end", "strand", "qualifiers"):
            assert key in feat

    def test_cds_feature_present(self, tmp_path):
        gb = tmp_path / "seq.gb"
        gb.write_text(GENBANK_CONTENT)
        result = annotate_from_genbank(str(gb))
        types = [f["type"] for f in result["features"]]
        assert "CDS" in types


class TestFindRestrictionSitesExtra:
    def test_returns_sorted_by_enzyme(self):
        # GFP-like sequence has known restriction sites
        seq = "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAG"
        sites = find_restriction_sites(seq)
        if len(sites) >= 2:
            names = [s["enzyme"] for s in sites]
            assert names == sorted(names)

    def test_each_site_has_required_keys(self):
        seq = "ATGGTGAGCAAGGGCGAGGAGCTGTTCACC"
        sites = find_restriction_sites(seq)
        for site in sites:
            assert "enzyme" in site
            assert "positions" in site
            assert "cut_count" in site

    def test_empty_position_list_excluded(self):
        seq = "AAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        sites = find_restriction_sites(seq)
        # All returned sites must have at least one position
        for site in sites:
            assert len(site["positions"]) > 0
