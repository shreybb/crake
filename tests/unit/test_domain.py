"""Unit tests for domain model."""
import pytest
from src.domain.part import BiologicalPart
from src.domain.plasmid import Plasmid, Feature
from src.domain.cloning_strategy import CloningStrategy, Primer


GFP_SEQ = "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAGCTGGACGGCGACGTAAACGGCCACAAGTTCAGCGTGTCCGGCGAGGGCGAGGGCGATGCCACCTACGGCAAGCTGACCCTGAAGTTCATCTGCACCACCGGCAAGCTGCCCGTGCCCTGGCCCACCCTCGTGACCACCCTGACCTACGGCGTGCAGTGCTTCAGCCGCTACCCCGACCACATGAAGCAGCACGACTTCTTCAAGTCCGCCATGCCCGAAGGCTACGTCCAGGAGCGCACCATCTTCTTCAAGGACGACGGCAACTACAAGACCCGCGCCGAGGTGAAGTTCGAGGGCGACACCCTGGTGAACCGCATCGAGCTGAAGGGCATCGACTTCAAGGAGGACGGCAACATCCTGGGGCACAAGCTGGAGTACAACTACAACAGCCACAACGTCTATATCATGGCCGACAAGCAGAAGAACGGCATCAAGGTGAACTTCAAGATCCGCCACAACATCGAGGACGGCAGCGTGCAGCTCGCCGACCACTACCAGCAGAACACCCCCATCGGCGACGGCCCCGTGCTGCTGCCCGACAACCACTACCTGAGCACCCAGTCCAAGCTGAGCAAAGACCCCAACGAGAAGCGCGATCACATGGTCCTGCTGGAGTTCGTGACCGCCGCCGGGATCACTCTCGGCATGGACGAGCTGTACAAG"

BACKBONE_SEQ = "ATCGATCGATCGATCG" * 500  # fake backbone


class TestBiologicalPart:
    def test_creates_valid_part(self):
        part = BiologicalPart(
            name="GFP",
            sequence=GFP_SEQ,
            part_type="reporter",
            compatible_hosts=("e_coli",),
        )
        assert part.name == "GFP"
        assert part.length == len(GFP_SEQ)
        assert part.sequence == GFP_SEQ.upper()

    def test_normalizes_sequence_to_uppercase(self):
        part = BiologicalPart(
            name="test",
            sequence="atcgatcg",
            part_type="other",
            compatible_hosts=("e_coli",),
        )
        assert part.sequence == "ATCGATCG"

    def test_rejects_empty_sequence(self):
        with pytest.raises(ValueError, match="empty sequence"):
            BiologicalPart(
                name="bad",
                sequence="",
                part_type="other",
                compatible_hosts=("e_coli",),
            )

    def test_rejects_invalid_bases(self):
        with pytest.raises(ValueError, match="invalid bases"):
            BiologicalPart(
                name="bad",
                sequence="ATCGXYZ",
                part_type="other",
                compatible_hosts=("e_coli",),
            )

    def test_is_immutable(self):
        part = BiologicalPart(
            name="GFP", sequence=GFP_SEQ, part_type="reporter",
            compatible_hosts=("e_coli",)
        )
        with pytest.raises((AttributeError, TypeError)):
            part.name = "other"  # type: ignore


class TestPlasmid:
    def test_creates_valid_plasmid(self):
        p = Plasmid(name="pTest", sequence=BACKBONE_SEQ)
        assert p.length == len(BACKBONE_SEQ)
        assert p.topology == "circular"

    def test_with_feature_returns_new_plasmid(self):
        p = Plasmid(name="pTest", sequence=BACKBONE_SEQ)
        feat = Feature(name="GFP", feature_type="CDS", start=0, end=720)
        p2 = p.with_feature(feat)
        assert len(p2.features) == 1
        assert len(p.features) == 0  # original unchanged

    def test_rejects_empty_sequence(self):
        with pytest.raises(ValueError):
            Plasmid(name="bad", sequence="")


class TestPrimer:
    def test_primer_length(self):
        fwd = Primer(
            name="GFP_fwd",
            sequence="GCGCATGGTGAGCAAGGGCGAGG",
            binding_region="ATGGTGAGCAAGGGCGAGG",
            overhang="GCGC",
        )
        assert fwd.length == 23
