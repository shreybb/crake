"""Unit tests for src/agent/commands.py and command_runner.py."""
from __future__ import annotations

import pytest

from src.agent.command_runner import _parse_genesearch, _parse_introduce_gene, introduce_gene_input
from src.agent.commands import COMMANDS, help_markdown, parse_input, validate_command


class TestParseInput:
    def test_plain_message_returns_none_command(self):
        cmd, args = parse_input("design a plasmid for GFP")
        assert cmd is None
        assert args == "design a plasmid for GFP"

    def test_slash_command_parsed(self):
        cmd, args = parse_input("/genesearch GFP in Aequorea victoria")
        assert cmd == "genesearch"
        assert args == "GFP in Aequorea victoria"

    def test_no_args(self):
        cmd, args = parse_input("/validate")
        assert cmd == "validate"
        assert args == ""


class TestValidateCommand:
    def test_unknown_command_raises(self):
        with pytest.raises(ValueError, match="Unknown command"):
            validate_command("nonexistent")

    def test_help_is_valid(self):
        validate_command("help")

    def test_known_command_ok(self):
        validate_command("fetch")

    def test_annotate_command_registered(self):
        validate_command("annotate")
        assert "annotate" in COMMANDS


class TestHelpMarkdown:
    def test_mentions_no_llm(self):
        assert "no chat model" in help_markdown().lower() or "slash" in help_markdown().lower()

    def test_lists_introduce_gene(self):
        assert "introduce-gene" in help_markdown()


class TestParseGenesearch:
    def test_in_syntax(self):
        inp = _parse_genesearch("GFP in Aequorea victoria")
        assert inp == {"gene_name": "GFP", "organism": "Aequorea victoria"}

    def test_space_separated(self):
        inp = _parse_genesearch("GFP Aequorea victoria")
        assert inp["gene_name"] == "GFP"
        assert "Aequorea" in inp["organism"]


class TestParseIntroduceGene:
    def test_full_syntax(self):
        inp = _parse_introduce_gene(
            "GFP in Aequorea victoria into agrobacterium goal: constitutive"
        )
        assert inp["gene_name"] == "GFP"
        assert inp["target_host"] == "agrobacterium"
        assert inp["expression_goal"] == "constitutive"

    def test_introduce_gene_command_registered(self):
        assert "introduce-gene" in COMMANDS
        assert "into <host>" in COMMANDS["introduce-gene"].usage


class TestIntroduceGeneInput:
    def test_form_fields(self):
        inp = introduce_gene_input("GFP", "Aequorea victoria", "yeast", "constitutive")
        assert inp["gene_name"] == "GFP"
        assert inp["target_host"] == "yeast"
