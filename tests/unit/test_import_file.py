"""Unit tests for import_file tool."""
from __future__ import annotations

import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq

from src.tools.import_file import import_sequence, _seqrecord_to_result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FASTA_CONTENT = ">pTest\nATGGAGCTGAACGATCGATCGATCGATCGATCG\n"

GENBANK_CONTENT = """\
LOCUS       pTest                     34 bp    DNA     linear   SYN 01-JAN-2025
DEFINITION  Test plasmid.
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
ORIGIN
        1 atggagctga acgatcgatc gatcgatcga tcg
//
"""


def _make_seqrecord(seq: str = "ATCGATCG", name: str = "TEST",
                    organism: str = "synthetic", topology: str = "linear") -> SeqRecord:
    record = SeqRecord(
        Seq(seq),
        id=name,
        name=name,
        description="Test record",
    )
    record.annotations["organism"] = organism
    record.annotations["topology"] = topology
    return record


# ---------------------------------------------------------------------------
# import_sequence — error paths
# ---------------------------------------------------------------------------

class TestImportSequenceErrors:
    def test_missing_file_returns_error(self, tmp_path):
        result = import_sequence(str(tmp_path / "nonexistent.gb"))
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_directory_path_returns_error(self, tmp_path):
        result = import_sequence(str(tmp_path))
        assert "error" in result

    def test_unsupported_extension_returns_error(self, tmp_path):
        f = tmp_path / "seq.txt"
        f.write_text("ATCG")
        result = import_sequence(str(f))
        assert "error" in result
        assert "Unsupported" in result["error"]

    def test_exception_returns_error_dict(self, tmp_path):
        f = tmp_path / "bad.gb"
        f.write_text("garbage")
        result = import_sequence(str(f))
        assert "error" in result


# ---------------------------------------------------------------------------
# import_sequence — FASTA
# ---------------------------------------------------------------------------

class TestImportFasta:
    def test_fasta_import_returns_sequence(self, tmp_path):
        fa = tmp_path / "seq.fa"
        fa.write_text(FASTA_CONTENT)
        result = import_sequence(str(fa))
        assert "sequence" in result
        assert result["sequence"] == "ATGGAGCTGAACGATCGATCGATCGATCGATCG"

    def test_fasta_import_accession(self, tmp_path):
        fa = tmp_path / "seq.fasta"
        fa.write_text(FASTA_CONTENT)
        result = import_sequence(str(fa))
        assert "accession" in result

    def test_fasta_length_correct(self, tmp_path):
        fa = tmp_path / "seq.fa"
        fa.write_text(FASTA_CONTENT)
        result = import_sequence(str(fa))
        assert result["length_bp"] == len("ATGGAGCTGAACGATCGATCGATCGATCGATCG")


# ---------------------------------------------------------------------------
# import_sequence — GenBank
# ---------------------------------------------------------------------------

class TestImportGenbank:
    def test_genbank_import_returns_sequence(self, tmp_path):
        gb = tmp_path / "seq.gb"
        gb.write_text(GENBANK_CONTENT)
        result = import_sequence(str(gb))
        assert "sequence" in result
        assert len(result["sequence"]) > 0

    def test_genbank_topology_preserved(self, tmp_path):
        gb = tmp_path / "seq.gb"
        gb.write_text(GENBANK_CONTENT)
        result = import_sequence(str(gb))
        assert "topology" in result

    def test_genbank_features_extracted(self, tmp_path):
        gb = tmp_path / "seq.gb"
        gb.write_text(GENBANK_CONTENT)
        result = import_sequence(str(gb))
        assert "features" in result
        assert isinstance(result["features"], list)

    def test_genbank_db_is_local_file(self, tmp_path):
        gb = tmp_path / "seq.gb"
        gb.write_text(GENBANK_CONTENT)
        result = import_sequence(str(gb))
        assert result.get("db") == "local_file"


# ---------------------------------------------------------------------------
# _seqrecord_to_result
# ---------------------------------------------------------------------------

class TestSeqrecordToResult:
    def test_basic_fields_present(self):
        record = _make_seqrecord("ATCGATCG", "GENE1", "Escherichia coli")
        result = _seqrecord_to_result(record, "/fake/path/GENE1.gb")
        for key in ("accession", "gene_name", "organism", "sequence", "length_bp",
                    "topology", "features", "db", "source_path", "suggested_host"):
            assert key in result

    def test_sequence_is_uppercase(self):
        record = _make_seqrecord("atcgatcg")
        result = _seqrecord_to_result(record, "test.gb")
        assert result["sequence"] == "ATCGATCG"

    def test_ecoli_organism_maps_to_ecoli_host(self):
        record = _make_seqrecord(organism="Escherichia coli")
        result = _seqrecord_to_result(record, "test.gb")
        assert result["suggested_host"] == "e_coli"

    def test_plant_organism_maps_to_agrobacterium_host(self):
        record = _make_seqrecord(organism="Arabidopsis thaliana")
        result = _seqrecord_to_result(record, "test.gb")
        assert result["suggested_host"] == "agrobacterium"

    def test_features_exclude_source(self):
        from Bio.SeqFeature import SeqFeature, SimpleLocation
        record = _make_seqrecord("ATCGATCGATCG")
        source_feat = SeqFeature(SimpleLocation(0, 12, 1), type="source")
        cds_feat = SeqFeature(
            SimpleLocation(0, 12, 1),
            type="CDS",
            qualifiers={"gene": ["gfp"]},
        )
        record.features = [source_feat, cds_feat]
        result = _seqrecord_to_result(record, "test.gb")
        # source feature should be excluded
        feat_types = [f["type"] for f in result["features"]]
        assert "source" not in feat_types
        assert "CDS" in feat_types

    def test_feature_with_note_qualifier(self):
        from Bio.SeqFeature import SeqFeature, SimpleLocation
        record = _make_seqrecord("ATCGATCGATCG")
        feat = SeqFeature(
            SimpleLocation(0, 6, 1),
            type="misc_feature",
            qualifiers={"note": ["my note"]},
        )
        record.features = [feat]
        result = _seqrecord_to_result(record, "test.gb")
        assert result["features"][0]["name"] == "my note"

    def test_feature_strand_none_defaults_to_one(self):
        from Bio.SeqFeature import SeqFeature, SimpleLocation
        record = _make_seqrecord("ATCGATCG")
        feat = SeqFeature(SimpleLocation(0, 4, None), type="CDS")
        record.features = [feat]
        result = _seqrecord_to_result(record, "test.gb")
        assert result["features"][0]["strand"] == 1

    def test_snapgene_import_calls_snapgene_reader(self, tmp_path):
        fake_dna = tmp_path / "test.dna"
        fake_dna.write_bytes(b"\x00" * 10)
        mock_record = _make_seqrecord("ATCGATCG")
        # snapgene_file_to_seqrecord is imported lazily inside _import_snapgene
        with patch("snapgene_reader.snapgene_file_to_seqrecord", return_value=mock_record):
            result = import_sequence(str(fake_dna))
        assert result["sequence"] == "ATCGATCG"
