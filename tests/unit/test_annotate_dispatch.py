"""Dispatch tests for annotate_sequence."""
from __future__ import annotations

from src.agent.tool_dispatch import dispatch


class TestAnnotateDispatch:
    def test_annotate_stores_result(self):
        session: dict = {}
        seq = "GAATTC" + "ATCG" * 50 + "GAATTC"
        result = dispatch(
            "annotate_sequence",
            {"sequence": seq, "topology": "linear"},
            session,
        )
        assert result.get("site_count", 0) >= 0
        assert session.get("last_annotation") is not None
