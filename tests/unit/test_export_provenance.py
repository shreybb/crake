"""Export protocol includes assembly provenance."""
from __future__ import annotations

from src.tools.export import write_protocol_md


class TestExportProvenance:
    def test_sequence_only_warning_in_protocol(self, tmp_path):
        assembly = {
            "method": "sequence_only",
            "provenance": "not_run",
            "topology": "linear",
            "product_length_bp": 100,
            "product_sequence": "A" * 100,
            "input_parts": [],
        }
        out = tmp_path / "protocol.md"
        write_protocol_md(assembly, {}, {"warnings": []}, "pTest", out)
        text = out.read_text()
        assert "not simulated" in text.lower()
        assert "Provenance" in text

    def test_simulated_provenance(self, tmp_path):
        assembly = {
            "method": "gibson",
            "provenance": "simulated",
            "topology": "circular",
            "product_length_bp": 5000,
            "input_parts": [{"name": "a", "length": 100}],
        }
        out = tmp_path / "protocol.md"
        write_protocol_md(assembly, {}, {}, "pTest", out)
        assert "simulated" in out.read_text().lower()
