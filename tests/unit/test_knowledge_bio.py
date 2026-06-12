"""Biological accuracy tests for the knowledge base JSON files."""

from __future__ import annotations

import json
from pathlib import Path

KB_DIR = Path("src/knowledge")


def _load(name: str) -> dict:
    return json.loads((KB_DIR / name).read_text())


# ---------------------------------------------------------------------------
# Issue P — pRS 2-micron vectors copy number consistency
# ---------------------------------------------------------------------------


class Test2MicronCopyNumber:
    """All 2-micron-origin yeast vectors must cite the same copy-number range.

    The 2-micron origin gives ~20–40 copies per cell under standard conditions.
    pYES2, pESC-*, and pRS 4xx vectors all carry this origin and should agree.
    """

    def setup_method(self):
        self.backbones = _load("backbones.json")["yeast"]

    def _assert_consistent_copy_number(self, vector_name: str) -> None:
        entry = self.backbones[vector_name]
        assert entry.get("ori") == "2-micron", f"{vector_name} must use 2-micron ori"
        notes = entry.get("notes", "")
        # Must not claim 15–20 (the old, low estimate) and must state 20–40
        assert "15" not in notes, (
            f"{vector_name} notes still reference 15 copies/cell — update to 20–40"
        )
        assert "20" in notes, f"{vector_name} notes must state copy number (~20–40 copies/cell)"

    def test_pRS416_copy_number_consistent(self):
        self._assert_consistent_copy_number("pRS416")

    def test_pRS415_copy_number_consistent(self):
        self._assert_consistent_copy_number("pRS415")

    def test_pRS414_copy_number_consistent(self):
        self._assert_consistent_copy_number("pRS414")

    def test_pRS413_copy_number_consistent(self):
        self._assert_consistent_copy_number("pRS413")

    def test_pYES2_copy_number_matches_pRS4xx(self):
        """pYES2 (2-micron) copy number must agree with pRS 2-micron range."""
        pyes2 = self.backbones["pYES2"]
        assert "20" in pyes2.get("notes", ""), (
            "pYES2 notes must state copy number in the 20–40 range"
        )

    def test_2micron_vectors_all_high_copy(self):
        two_micron = [k for k, v in self.backbones.items() if v.get("ori") == "2-micron"]
        for name in two_micron:
            assert self.backbones[name]["copy_number"] == "high", (
                f"{name} must be copy_number='high'"
            )


# ---------------------------------------------------------------------------
# Promoter expression_type consistency
# ---------------------------------------------------------------------------


class TestPromoterExpressionType:
    def setup_method(self):
        data = _load("promoters.json")
        self.all_promoters: list[dict] = []
        for host_group in data.values():
            for name, attrs in host_group.items():
                self.all_promoters.append({"name": name, **attrs})

    def test_all_promoters_have_expression_type(self):
        for p in self.all_promoters:
            assert "expression_type" in p, f"Promoter '{p['name']}' is missing 'expression_type'"

    def test_inducible_promoters_have_inducer(self):
        for p in self.all_promoters:
            if p.get("expression_type") == "inducible":
                assert "inducer" in p, f"Inducible promoter '{p['name']}' is missing 'inducer'"

    def test_MET25_is_repressible_not_inducible(self):
        """MET25 is methionine-repressible, not inducible — a common point of confusion."""
        data = _load("promoters.json")
        met25 = data["yeast"]["MET25"]
        assert met25["expression_type"] == "repressible"
        assert met25.get("inducible") is False


# ---------------------------------------------------------------------------
# Binary vector T-DNA borders
# ---------------------------------------------------------------------------


class TestBinaryVectors:
    def test_all_plant_binary_vectors_have_tdna_borders(self):
        data = _load("backbones.json")
        for name, attrs in data.get("plant_binary", {}).items():
            assert attrs.get("t_dna_borders") is True, (
                f"Binary vector '{name}' must have t_dna_borders=true"
            )

    def test_plant_binary_vectors_have_two_selection_markers(self):
        """Binary vectors need both a plant and a bacterial selectable marker."""
        data = _load("backbones.json")
        for name, attrs in data.get("plant_binary", {}).items():
            assert "plant_selection" in attrs, f"Binary vector '{name}' missing plant_selection"
            assert "bacterial_selection" in attrs, (
                f"Binary vector '{name}' missing bacterial_selection"
            )
