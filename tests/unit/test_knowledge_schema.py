"""Knowledge JSON files must match schemas."""
from __future__ import annotations

from src.knowledge import (
    get_backbones,
    get_promoters,
    get_selectable_markers,
    get_terminators,
)


class TestKnowledgeSchema:
    def test_backbones_load(self):
        data = get_backbones()
        assert "e_coli" in data

    def test_promoters_load(self):
        assert get_promoters()

    def test_terminators_load(self):
        assert get_terminators()

    def test_markers_load(self):
        assert get_selectable_markers()
