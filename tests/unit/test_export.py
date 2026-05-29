"""Unit tests for export tool."""
import csv

import pytest
from Bio import SeqIO

from src.tools.export import (
    write_fasta,
    write_genbank,
    write_plasmid_map,
    write_primers_csv,
    write_protocol_md,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

GFP = (
    "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAGCTGGAC"
    "GGCGACGTAAACGGCCACAAGTTCAGCGTGTCCGGCGAGGGCGAGGGCGATGCCACCTAC"
    "GCGTTGTAA"  # stop codon so ORF detection works
)

ASSEMBLY_JSON = {
    "success": True,
    "method": "gibson",
    "topology": "circular",
    "product_length_bp": len(GFP),
    "product_sequence": GFP,
    "input_parts": [
        {"name": "backbone", "length": 5000},
        {"name": "GFP_insert", "length": len(GFP)},
    ],
}

VALIDATION_JSON = {
    "name": "pTest",
    "length_bp": len(GFP),
    "topology": "circular",
    "gc_analysis": {"overall_gc_percent": 58.3, "flagged_windows": []},
    "orfs": [{"strand": 1, "frame": 0, "start_nt": 0, "end_nt": len(GFP), "length_aa": 42}],
    "restriction_sites": [
        {"enzyme": "EcoRI", "positions": [10], "count": 1},
    ],
    "warnings": [],
    "passed_checks": True,
}

PRIMERS_JSON = {
    "primer_pairs": [
        {
            "rank": 0,
            "forward": {
                "binding_region": "ATGGTGAGCAAGGGCGAGG",
                "full_sequence": "GCGCATGGTGAGCAAGGGCGAGG",
                "tm_celsius": 61.2,
                "gc_percent": 57.1,
                "length": 23,
            },
            "reverse": {
                "binding_region": "TTACAGCATCGTCCTTGTA",
                "full_sequence": "GCGCTTACAGCATCGTCCTTGTA",
                "tm_celsius": 59.8,
                "gc_percent": 52.2,
                "length": 23,
            },
            "product_size_bp": len(GFP),
            "penalty": 0.12,
        }
    ]
}


@pytest.fixture
def tmp(tmp_path):
    return tmp_path


# ---------------------------------------------------------------------------
# write_fasta
# ---------------------------------------------------------------------------

class TestWriteFasta:
    def test_creates_file(self, tmp):
        out = tmp / "out.fa"
        write_fasta(GFP, "pTest", out)
        assert out.exists()

    def test_sequence_matches(self, tmp):
        out = tmp / "out.fa"
        write_fasta(GFP, "pTest", out)
        record = SeqIO.read(str(out), "fasta")
        assert str(record.seq) == GFP

    def test_name_in_header(self, tmp):
        out = tmp / "out.fa"
        write_fasta(GFP, "pMyCoolGene", out)
        assert "pMyCoolGene" in out.read_text()


# ---------------------------------------------------------------------------
# write_genbank
# ---------------------------------------------------------------------------

class TestWriteGenbank:
    def test_creates_file(self, tmp):
        out = tmp / "out.gb"
        write_genbank(ASSEMBLY_JSON, VALIDATION_JSON, "pTest", out)
        assert out.exists()

    def test_parseable_by_biopython(self, tmp):
        out = tmp / "out.gb"
        write_genbank(ASSEMBLY_JSON, VALIDATION_JSON, "pTest", out)
        record = SeqIO.read(str(out), "genbank")
        assert str(record.seq) == GFP

    def test_orf_features_added(self, tmp):
        out = tmp / "out.gb"
        write_genbank(ASSEMBLY_JSON, VALIDATION_JSON, "pTest", out)
        record = SeqIO.read(str(out), "genbank")
        cds_features = [f for f in record.features if f.type == "CDS"]
        assert len(cds_features) == 1

    def test_restriction_site_features_added(self, tmp):
        out = tmp / "out.gb"
        write_genbank(ASSEMBLY_JSON, VALIDATION_JSON, "pTest", out)
        record = SeqIO.read(str(out), "genbank")
        binding_features = [f for f in record.features if f.type == "misc_binding"]
        assert len(binding_features) >= 1

    def test_topology_annotation(self, tmp):
        out = tmp / "out.gb"
        write_genbank(ASSEMBLY_JSON, VALIDATION_JSON, "pTest", out)
        record = SeqIO.read(str(out), "genbank")
        assert record.annotations.get("topology") == "circular"

    def test_empty_validation_still_writes(self, tmp):
        out = tmp / "out.gb"
        write_genbank(ASSEMBLY_JSON, {}, "pTest", out)
        assert out.exists()

    def test_restriction_site_feature_length_not_always_6(self, tmp):
        """NotI recognition site is 8 bp — feature end must be pos + 8, not pos + 6."""
        out = tmp / "out.gb"
        validation_with_not1 = {
            **VALIDATION_JSON,
            "restriction_sites": [
                {"enzyme": "NotI", "positions": [5], "count": 1},
            ],
        }
        write_genbank(ASSEMBLY_JSON, validation_with_not1, "pTest", out)
        record = SeqIO.read(str(out), "genbank")
        not1_features = [
            f for f in record.features
            if f.type == "misc_binding" and "NotI" in str(f.qualifiers.get("note", ""))
        ]
        assert len(not1_features) == 1
        feat = not1_features[0]
        # NotI recognition site (GCGGCCGC) = 8 bp → end should be start + 8
        assert int(feat.location.end) - int(feat.location.start) == 8

    def test_ecori_site_feature_length_is_6(self, tmp):
        """EcoRI recognition site is 6 bp — standard case must still work."""
        out = tmp / "out.gb"
        write_genbank(ASSEMBLY_JSON, VALIDATION_JSON, "pTest", out)
        record = SeqIO.read(str(out), "genbank")
        ecori_features = [
            f for f in record.features
            if f.type == "misc_binding" and "EcoRI" in str(f.qualifiers.get("note", ""))
        ]
        assert len(ecori_features) == 1
        feat = ecori_features[0]
        assert int(feat.location.end) - int(feat.location.start) == 6

    def test_restriction_site_annotated_at_recognition_sequence_not_cut_site(self, tmp):
        """GenBank feature must start at the recognition sequence, not the cut site.

        BioPython Analysis.full() returns 1-based CUT positions; export.py must
        convert to 0-based recognition-sequence start coordinates.

        EcoRI (G^AATTC) has fst5cut=1 (cuts after the G).
        For a recognition site starting at 0-based position 5:
          BioPython returns cut_pos = 5 + 1 + 1 = 7
          Correct recog_start = 7 - 1 - 1 = 5
          Wrong (old bug): SimpleLocation(7, 13) → seq[7:13] ≠ GAATTC
          Correct:         SimpleLocation(5, 11) → seq[5:11] == GAATTC
        """
        # Build a sequence with EcoRI (GAATTC) at 0-based position 5
        sequence = "AAAAAGAATTCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        from Bio.Restriction import Analysis, EcoRI
        from Bio.Seq import Seq as BioSeq
        cut_pos = Analysis([EcoRI], BioSeq(sequence), linear=True).full()[EcoRI][0]
        assembly = {**ASSEMBLY_JSON, "product_sequence": sequence, "product_length_bp": len(sequence)}
        validation = {
            **VALIDATION_JSON,
            "restriction_sites": [{"enzyme": "EcoRI", "positions": [cut_pos], "count": 1}],
        }
        out = tmp / "out.gb"
        write_genbank(assembly, validation, "pTest", out)
        record = SeqIO.read(str(out), "genbank")
        ecori_feats = [f for f in record.features if "EcoRI" in str(f.qualifiers.get("note", ""))]
        assert len(ecori_feats) == 1
        feat = ecori_feats[0]
        # Feature must be positioned over the actual GAATTC recognition sequence
        start = int(feat.location.start)
        assert sequence[start:start + 6] == "GAATTC", (
            f"Feature at {start} spans '{sequence[start:start+6]}', expected 'GAATTC'"
        )


# ---------------------------------------------------------------------------
# write_primers_csv
# ---------------------------------------------------------------------------

class TestWritePrimersCsv:
    def test_creates_file(self, tmp):
        out = tmp / "primers.csv"
        write_primers_csv(PRIMERS_JSON["primer_pairs"], out)
        assert out.exists()

    def test_has_required_columns(self, tmp):
        out = tmp / "primers.csv"
        write_primers_csv(PRIMERS_JSON["primer_pairs"], out)
        with out.open() as fh:
            reader = csv.DictReader(fh)
            row = next(reader)
        assert set(row.keys()) == {"Name", "Sequence", "Scale", "Purification"}

    def test_forward_primer_row(self, tmp):
        out = tmp / "primers.csv"
        write_primers_csv(PRIMERS_JSON["primer_pairs"], out)
        with out.open() as fh:
            rows = list(csv.DictReader(fh))
        fwd_rows = [r for r in rows if "FWD" in r["Name"]]
        assert len(fwd_rows) == 1
        assert fwd_rows[0]["Sequence"] == "GCGCATGGTGAGCAAGGGCGAGG"

    def test_reverse_primer_row(self, tmp):
        out = tmp / "primers.csv"
        write_primers_csv(PRIMERS_JSON["primer_pairs"], out)
        with out.open() as fh:
            rows = list(csv.DictReader(fh))
        rev_rows = [r for r in rows if "REV" in r["Name"]]
        assert len(rev_rows) == 1

    def test_empty_pairs_produces_header_only(self, tmp):
        out = tmp / "primers.csv"
        write_primers_csv([], out)
        with out.open() as fh:
            rows = list(csv.DictReader(fh))
        assert rows == []


# ---------------------------------------------------------------------------
# write_protocol_md
# ---------------------------------------------------------------------------

class TestWriteProtocolMd:
    def test_creates_file(self, tmp):
        out = tmp / "protocol.md"
        write_protocol_md(ASSEMBLY_JSON, PRIMERS_JSON, VALIDATION_JSON, "pTest", out)
        assert out.exists()

    def test_contains_construct_name(self, tmp):
        out = tmp / "protocol.md"
        write_protocol_md(ASSEMBLY_JSON, PRIMERS_JSON, VALIDATION_JSON, "pMyGene", out)
        assert "pMyGene" in out.read_text()

    def test_contains_assembly_method(self, tmp):
        out = tmp / "protocol.md"
        write_protocol_md(ASSEMBLY_JSON, PRIMERS_JSON, VALIDATION_JSON, "pTest", out)
        content = out.read_text()
        assert "Gibson" in content

    def test_contains_primer_sequences(self, tmp):
        out = tmp / "protocol.md"
        write_protocol_md(ASSEMBLY_JSON, PRIMERS_JSON, VALIDATION_JSON, "pTest", out)
        assert "GCGCATGGTGAGCAAGGGCGAGG" in out.read_text()

    def test_contains_restriction_sites(self, tmp):
        out = tmp / "protocol.md"
        write_protocol_md(ASSEMBLY_JSON, PRIMERS_JSON, VALIDATION_JSON, "pTest", out)
        assert "EcoRI" in out.read_text()

    def test_warnings_shown_when_present(self, tmp):
        out = tmp / "protocol.md"
        validation_with_warnings = {**VALIDATION_JSON, "warnings": ["High GC: 72%"]}
        write_protocol_md(ASSEMBLY_JSON, PRIMERS_JSON, validation_with_warnings, "pTest", out)
        assert "High GC: 72%" in out.read_text()

    def test_empty_inputs_still_writes(self, tmp):
        out = tmp / "protocol.md"
        write_protocol_md({}, {}, {}, "pTest", out)
        assert out.exists()


# ---------------------------------------------------------------------------
# write_plasmid_map
# ---------------------------------------------------------------------------

class TestWritePlasmidMap:
    def test_creates_svg_file(self, tmp):
        gb_path = tmp / "out.gb"
        write_genbank(ASSEMBLY_JSON, VALIDATION_JSON, "pTest", gb_path)

        svg_path = tmp / "map.svg"
        write_plasmid_map(gb_path, svg_path)
        assert svg_path.exists()

    def test_svg_contains_xml(self, tmp):
        gb_path = tmp / "out.gb"
        write_genbank(ASSEMBLY_JSON, VALIDATION_JSON, "pTest", gb_path)

        svg_path = tmp / "map.svg"
        write_plasmid_map(gb_path, svg_path)
        content = svg_path.read_text()
        assert "<svg" in content or "<?xml" in content
