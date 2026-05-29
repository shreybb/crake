"""Unit tests for app.py pre-flight logic.

We cannot import app.py directly (it runs Streamlit module-level code), so
we test the biological correctness of the constants by:
  1. Grepping the source for the regex pattern string and compiling it ourselves.
  2. Verifying the unsupported-host warning message text.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_source() -> str:
    return open("app.py").read()


def _compile_unsupported_regex(source: str) -> re.Pattern:
    """Extract the full pattern string and compile it."""
    # The pattern is two concatenated raw-string literals on consecutive lines.
    # Collect all r'...' or r"..." segments inside re.compile(...)
    m = re.search(
        r"_UNSUPPORTED_HOST_RE\s*=\s*re\.compile\(([\s\S]+?),\s*re\.IGNORECASE",
        source,
    )
    assert m, "Could not locate _UNSUPPORTED_HOST_RE"
    block = m.group(1)
    # Join every raw-string fragment found in the block
    parts = re.findall(r"r'([^']*)'|r\"([^\"]*)\"|'([^']*)'|\"([^\"]*)\"", block)
    pattern = "".join("".join(p) for p in parts)
    return re.compile(pattern, re.IGNORECASE)


def _extract_host_support_msg(source: str) -> str:
    """Return _HOST_SUPPORT_MSG value by joining its string fragments."""
    m = re.search(
        r"_HOST_SUPPORT_MSG\s*=\s*\(([\s\S]+?)\n\)",
        source,
    )
    assert m, "Could not locate _HOST_SUPPORT_MSG"
    block = m.group(1)
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', block)
    return "".join(parts)


# ---------------------------------------------------------------------------
# Issue M — _UNSUPPORTED_HOST_RE no longer blocks pichia / kluyveromyces
# ---------------------------------------------------------------------------

class TestUnsupportedHostRegex:
    def setup_method(self):
        src = _read_source()
        self.regex = _compile_unsupported_regex(src)
        self.msg = _extract_host_support_msg(src)

    def test_pichia_not_blocked(self):
        """Pichia now routes to yeast via infer_host; should not be blocked."""
        assert not self.regex.search("optimize GFP for Pichia pastoris")

    def test_kluyveromyces_not_blocked(self):
        """Kluyveromyces now routes to yeast; should not be blocked."""
        assert not self.regex.search("introduce lacZ into Kluyveromyces lactis")

    def test_aspergillus_still_blocked(self):
        """Aspergillus is truly unsupported — should still trigger warning."""
        assert self.regex.search("express protein in Aspergillus niger")

    def test_streptomyces_still_blocked(self):
        assert self.regex.search("clone into Streptomyces coelicolor")

    def test_bacillus_subtilis_still_blocked(self):
        assert self.regex.search("optimize for Bacillus subtilis")

    def test_candida_albicans_still_blocked(self):
        """C. albicans has a non-standard genetic code — warning must remain."""
        assert self.regex.search("codon-optimize for Candida albicans")

    def test_fusarium_still_blocked(self):
        assert self.regex.search("express GFP in Fusarium oxysporum")

    def test_e_coli_not_blocked(self):
        assert not self.regex.search("introduce GFP into E. coli")

    def test_saccharomyces_not_blocked(self):
        assert not self.regex.search("design for Saccharomyces cerevisiae")

    def test_host_support_msg_mentions_partial_yeast_support(self):
        """Updated message should explain non-cerevisiae yeast partial support."""
        assert "pichia" in self.msg.lower() or "non-cerevisiae" in self.msg.lower()


