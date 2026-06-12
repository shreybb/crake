"""Tests for ConstructSession."""

from __future__ import annotations

from src.session.construct import (
    AssemblyProvenance,
    AssemblyRecord,
    ConstructSession,
    LoadedSequence,
    WorkflowStage,
)
from src.session.streamlit_adapter import apply_to_state, session_from_state


class TestConstructSession:
    def test_round_trip_state_dict(self):
        cs = ConstructSession(
            sequence=LoadedSequence(
                sequence="ATGAAA",
                gene_name="test",
                topology="linear",
                source="import",
            ),
        )
        state: dict = {}
        apply_to_state(cs, state)
        restored = session_from_state(state)
        assert restored.sequence is not None
        assert restored.sequence.sequence == "ATGAAA"

    def test_promote_optimized(self):
        cs = ConstructSession(
            sequence=LoadedSequence(sequence="ATGAAATGA", gene_name="gfp", source="fetch"),
        )
        cs.promote_optimized(
            {
                "optimized_sequence": "ATGCCC",
                "gc_before": 50,
                "gc_after": 55,
                "host": "e_coli",
            }
        )
        assert cs.sequence is not None
        assert cs.sequence.sequence == "ATGCCC"
        assert cs.workflow_stage() == WorkflowStage.OPTIMIZED

    def test_record_assembly_failed_does_not_set(self):
        cs = ConstructSession()
        cs.record_assembly({"success": False, "error": "no product"})
        assert cs.assembly is None

    def test_export_blocks_without_assembly(self):
        cs = ConstructSession(
            sequence=LoadedSequence(sequence="ATGAAATGA", topology="linear"),
        )
        try:
            cs.assembly_for_export(allow_sequence_only=False)
            assert False, "expected ValueError"
        except ValueError:
            pass

    def test_export_sequence_only(self):
        cs = ConstructSession(
            sequence=LoadedSequence(sequence="ATGAAATGA", topology="circular"),
        )
        rec = cs.assembly_for_export(allow_sequence_only=True)
        assert rec.provenance == AssemblyProvenance.NOT_RUN
        assert rec.method == "sequence_only"

    def test_assembly_from_legacy_dict(self):
        rec = AssemblyRecord.from_dict(
            {
                "success": True,
                "method": "gibson",
                "product_sequence": "ATGC",
            }
        )
        assert rec is not None
        assert rec.provenance == AssemblyProvenance.SIMULATED
