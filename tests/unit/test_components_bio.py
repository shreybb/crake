"""Biological accuracy tests for src/ui/components.py.

Cannot import components.py directly (it triggers Streamlit at module level),
so pure-logic values are extracted from the source text using regex and exec().
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

_COMPONENTS_SRC = (
    Path(__file__).parent.parent.parent / "src" / "ui" / "components.py"
).read_text()


def _extract_host_map() -> dict:
    """Extract _HOST_DISPLAY_TO_KEY from source text."""
    m = re.search(
        r"_HOST_DISPLAY_TO_KEY\s*=\s*(\{[^}]+\})",
        _COMPONENTS_SRC,
        re.DOTALL,
    )
    assert m, "_HOST_DISPLAY_TO_KEY not found in components.py"
    ns: dict = {}
    exec(f"result = {m.group(1)}", ns)  # noqa: S102
    return ns["result"]


def _extract_inducible_pattern() -> re.Pattern:
    """Extract the _INDUCIBLE_KEYWORDS compiled regex from source text.

    Strips inline # comments from the re.compile() block before exec so
    that comment lines inside the call don't cause a SyntaxError.
    """
    m = re.search(
        r"_INDUCIBLE_KEYWORDS\s*=\s*re\.compile\(\s*(.*?)\n\)",
        _COMPONENTS_SRC,
        re.DOTALL,
    )
    assert m, "_INDUCIBLE_KEYWORDS not found in components.py"
    raw = m.group(1)
    # Remove Python # comments (not inside strings)
    cleaned = re.sub(r"#[^\n]*", "", raw)
    ns: dict = {"re": re}
    exec(f"result = re.compile({cleaned})", ns)  # noqa: S102
    return ns["result"]


_HOST_MAP = _extract_host_map()
_INDUCIBLE_RE = _extract_inducible_pattern()


# ---------------------------------------------------------------------------
# Issue T: sidebar launcher must expose agrobacterium host
# ---------------------------------------------------------------------------

class TestHostDisplayMap:
    def test_agrobacterium_key_present(self):
        """Agrobacterium must be reachable from the GUI launcher (Issue T)."""
        values = list(_HOST_MAP.values())
        assert "agrobacterium" in values, (
            "agrobacterium missing from _HOST_DISPLAY_TO_KEY — "
            "users cannot access plant T-DNA workflow via the GUI"
        )

    def test_agrobacterium_label_mentions_plant(self):
        """Display label should indicate plant context to avoid confusion."""
        label = next(
            (k for k, v in _HOST_MAP.items() if v == "agrobacterium"), None
        )
        assert label is not None
        assert "plant" in label.lower() or "agrobacterium" in label.lower()

    def test_all_four_standard_hosts_present(self):
        """e_coli, yeast, plant_nuclear, and agrobacterium all required."""
        values = set(_HOST_MAP.values())
        for expected in ("e_coli", "yeast", "plant_nuclear", "agrobacterium"):
            assert expected in values, f"{expected} missing from _HOST_DISPLAY_TO_KEY"

    def test_no_invalid_host_values(self):
        """All values must be recognised host identifiers."""
        valid = {"e_coli", "yeast", "plant_nuclear", "agrobacterium"}
        for val in _HOST_MAP.values():
            assert val in valid, f"Unknown host value '{val}' in _HOST_DISPLAY_TO_KEY"


# ---------------------------------------------------------------------------
# Issue U: inducible keyword regex must not match trans-activators or enzymes
# ---------------------------------------------------------------------------

class TestInducibleKeywordsRegex:
    # Things that SHOULD trigger the callout
    def test_gal1_matches(self):
        assert _INDUCIBLE_RE.search("using the GAL1 promoter")

    def test_gal10_matches(self):
        assert _INDUCIBLE_RE.search("driven by GAL10")

    def test_pgal1_matches(self):
        assert _INDUCIBLE_RE.search("cloned under pGAL1")

    def test_iptg_inducible_matches(self):
        assert _INDUCIBLE_RE.search("IPTG-inducible expression")

    def test_arabinose_matches(self):
        assert _INDUCIBLE_RE.search("araBAD promoter activated by L-arabinose")

    def test_glucose_repressed_matches(self):
        """glucose-repressed is the correct catabolite repression description."""
        assert _INDUCIBLE_RE.search("GAL1 is glucose-repressed")

    def test_inducible_promoter_phrase_matches(self):
        assert _INDUCIBLE_RE.search("using an inducible promoter for tight control")

    # Things that must NOT trigger (biological false positives — Issue U)
    def test_gal4_does_not_match(self):
        """GAL4 is a transcription factor (Gal4p), not a promoter."""
        assert not _INDUCIBLE_RE.search(
            "We expressed GAL4 as the activator in a two-hybrid assay"
        ), "GAL4 should not trigger inducible callout — it is a trans-activator protein"

    def test_gal7_does_not_match(self):
        """GAL7 encodes galactose-1-phosphate uridylyltransferase — a metabolic enzyme."""
        assert not _INDUCIBLE_RE.search(
            "The GAL7 deletion strain cannot grow on galactose"
        ), "GAL7 should not trigger inducible callout — it is a metabolic enzyme"

    def test_galactose_repressed_does_not_match(self):
        """galactose-repressed is biologically wrong for GAL promoters.
        GAL1/GAL10 are galactose-ACTIVATED, not repressed.  The term was
        removed to avoid false callouts when a researcher describes galactose
        metabolism (e.g. 'ARG1 is galactose-repressed').
        """
        assert not _INDUCIBLE_RE.search(
            "ARG1 expression is galactose-repressed in rich media"
        ), (
            "galactose-repressed should not trigger the inducible callout — "
            "GAL promoters are galactose-ACTIVATED; the term was removed to avoid "
            "false positives for non-GAL galactose-regulated genes"
        )
