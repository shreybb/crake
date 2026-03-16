"""Unit tests for the slash-command parser and expander."""
from __future__ import annotations

import pytest

from src.agent.commands import COMMANDS, expand, help_markdown, parse_input


class TestParseInput:
    def test_plain_text_returns_none_command(self):
        cmd, args = parse_input("find me a plant gene")
        assert cmd is None
        assert args == "find me a plant gene"

    def test_slash_command_splits_name_and_args(self):
        cmd, args = parse_input("/genesearch find an aquatic plant")
        assert cmd == "genesearch"
        assert args == "find an aquatic plant"

    def test_command_without_args(self):
        cmd, args = parse_input("/validate")
        assert cmd == "validate"
        assert args == ""

    def test_command_is_lowercased(self):
        cmd, _ = parse_input("/GeneSearch query")
        assert cmd == "genesearch"

    def test_leading_whitespace_stripped(self):
        cmd, args = parse_input("  /fetch NM_001234  ")
        assert cmd == "fetch"
        assert args == "NM_001234"

    def test_args_preserve_internal_spaces(self):
        cmd, args = parse_input("/genesearch find an aquatic plant we can edit to glow")
        assert args == "find an aquatic plant we can edit to glow"


class TestExpand:
    def test_known_command_returns_string(self):
        prompt = expand("genesearch", "find a glowing aquatic plant")
        assert isinstance(prompt, str)
        assert "find a glowing aquatic plant" in prompt

    def test_args_interpolated_into_template(self):
        prompt = expand("suggest", "agrobacterium")
        assert "agrobacterium" in prompt

    def test_validate_no_args(self):
        prompt = expand("validate", "")
        assert "validate" in prompt.lower()

    def test_export_with_name(self):
        prompt = expand("export", "pMyGlowPlant")
        assert "pMyGlowPlant" in prompt

    def test_help_returns_none(self):
        assert expand("help", "") is None

    def test_unknown_command_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown command /bogus"):
            expand("bogus", "args")

    def test_all_known_commands_expand_without_error(self):
        for name in COMMANDS:
            result = expand(name, "test_arg")
            assert isinstance(result, str)
            assert len(result) > 0


class TestHelpMarkdown:
    def test_contains_all_command_names(self):
        md = help_markdown()
        for name in COMMANDS:
            assert f"/{name}" in md

    def test_contains_help_entry(self):
        assert "/help" in help_markdown()

    def test_returns_string(self):
        assert isinstance(help_markdown(), str)
