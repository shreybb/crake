"""Tests for curated knowledge-base part enumeration."""
from __future__ import annotations

from src.tools.knowledge_parts import list_part_names


class TestListPartNames:
    def test_returns_all_four_keys(self):
        parts = list_part_names()
        assert set(parts.keys()) == {"backbones", "promoters", "terminators", "markers"}

    def test_backbones_contains_known_ecoli_vectors(self):
        assert "pET-28a" in list_part_names()["backbones"]

    def test_all_lists_non_empty(self):
        for key, names in list_part_names().items():
            assert len(names) > 0, f"Expected non-empty list for {key}"

    def test_returns_new_dict_each_call(self):
        assert list_part_names() is not list_part_names()
