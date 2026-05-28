"""Slash command definitions and parser for the Crake UI.

Commands are executed directly via :mod:`command_runner` (no LLM).

Usage:
    /genesearch GFP in Aequorea victoria
    /fetch NM_001234
    /suggest agrobacterium
    /targets crispr
    /optimize plant_nuclear
    /primers ATTB1 ATTB2
    /assemble gibson backbone.fa
    /validate
    /export pMyConstruct
    /help
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    usage: str


COMMANDS: dict[str, Command] = {
    c.name: c
    for c in [
        Command(
            name="genesearch",
            description="Search NCBI for a gene (gene + source organism required)",
            usage="/genesearch <gene> in <organism>",
        ),
        Command(
            name="fetch",
            description="Fetch a sequence by NCBI or UniProt accession",
            usage="/fetch <accession>",
        ),
        Command(
            name="suggest",
            description="Suggest vector backbones and regulatory parts for a host",
            usage="/suggest <host>",
        ),
        Command(
            name="targets",
            description="Find edit target sites in the loaded sequence",
            usage="/targets <crispr|restriction|homologous> [pam|position]",
        ),
        Command(
            name="optimize",
            description="Codon-optimise the loaded sequence for a host",
            usage="/optimize <host>",
        ),
        Command(
            name="primers",
            description="Design PCR primers for the loaded sequence",
            usage="/primers [overhang_fwd] [overhang_rev]",
        ),
        Command(
            name="assemble",
            description="Simulate Gibson or restriction-ligation assembly (needs 2 fragments)",
            usage="/assemble gibson <file|sequence> | /assemble restriction_ligation <enzymes…> <file>",
        ),
        Command(
            name="validate",
            description="Validate the current construct",
            usage="/validate",
        ),
        Command(
            name="export",
            description="Export GenBank, FASTA, SVG map, primers CSV, and protocol",
            usage="/export <name>",
        ),
        Command(
            name="load",
            description="Load a sequence from a local file (.dna, .gb, .fa)",
            usage="/load <path>",
        ),
        Command(
            name="introduce-gene",
            description="Fetch CDS, codon-optimise, and suggest parts for a host",
            usage="/introduce-gene <gene> in <organism> into <host> [goal: <goal>]",
        ),
    ]
}


def parse_input(text: str) -> tuple[str | None, str]:
    """Return (command_name, args) if text starts with /, else (None, text)."""
    text = text.strip()
    if not text.startswith("/"):
        return None, text
    parts = text[1:].split(None, 1)
    cmd_name = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""
    return cmd_name, args


def validate_command(cmd_name: str) -> None:
    """Raise ValueError if ``cmd_name`` is not a known command (except help)."""
    if cmd_name == "help":
        return
    if cmd_name not in COMMANDS:
        known = ", ".join(f"/{c}" for c in sorted(COMMANDS))
        raise ValueError(f"Unknown command /{cmd_name}. Available: {known}")


def help_markdown() -> str:
    """Render a compact command reference as Markdown."""
    lines = [
        "**Crake commands** (run directly — no chat model required)\n",
        "Use the sidebar **Introduce a Gene** form for the full pipeline, "
        "or type a slash command below.\n",
    ]
    for cmd in COMMANDS.values():
        lines.append(f"`{cmd.usage}`  \n{cmd.description}")
    lines.append("`/help`  \nShow this message")
    return "\n\n".join(lines)
