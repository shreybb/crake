"""Slash command definitions and parser for the Crake chat interface.

Commands are expanded into structured prompts that guide the agent to call
the right tools. The agent still reasons freely — commands just give it
a precise starting instruction so the user doesn't have to write full sentences.

Usage:
    /genesearch find an aquatic plant we can easily edit to induce a glow
    /fetch NM_001234
    /suggest agrobacterium
    /targets crispr
    /optimize plant_nuclear
    /primers ATTB1 ATTB2
    /assemble gibson
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
    prompt_template: str  # {args} is replaced with the user's arguments


COMMANDS: dict[str, Command] = {
    c.name: c
    for c in [
        Command(
            name="genesearch",
            description="Search for a gene or organism by natural language query",
            usage="/genesearch <query>",
            prompt_template=(
                "The user wants to find a gene sequence. Query: \"{args}\". "
                "Interpret their intent, choose an appropriate gene_name and organism, "
                "then call search_gene. Summarise what you found and why it fits."
            ),
        ),
        Command(
            name="fetch",
            description="Fetch a sequence directly by NCBI or UniProt accession",
            usage="/fetch <accession>",
            prompt_template=(
                "Fetch the sequence with accession \"{args}\" using fetch_by_accession."
            ),
        ),
        Command(
            name="suggest",
            description="Suggest vector backbones and regulatory parts for a host",
            usage="/suggest <host>",
            prompt_template=(
                "Suggest appropriate vector backbones and parts for the host \"{args}\" "
                "using suggest_parts. Explain each recommendation briefly."
            ),
        ),
        Command(
            name="targets",
            description="Find edit target sites in the loaded sequence",
            usage="/targets <method> [position]",
            prompt_template=(
                "Find edit target sites using method \"{args}\" on the current sequence "
                "stored in session. Use find_target_sites. "
                "Summarise the top candidates and recommend the best one."
            ),
        ),
        Command(
            name="optimize",
            description="Codon-optimise the loaded sequence for a host",
            usage="/optimize <host>",
            prompt_template=(
                "Codon-optimise the current sequence for the host \"{args}\" "
                "using optimize_codons."
            ),
        ),
        Command(
            name="primers",
            description="Design PCR primers for the loaded sequence",
            usage="/primers [overhang_fwd] [overhang_rev]",
            prompt_template=(
                "Design PCR primers for the current sequence using design_primers. "
                "Extra arguments (overhangs, Tm): \"{args}\". "
                "Parse any overhangs or Tm the user specified, pass them through."
            ),
        ),
        Command(
            name="assemble",
            description="Simulate in-vitro assembly (gibson or restriction_ligation)",
            usage="/assemble <method> [enzymes…]",
            prompt_template=(
                "Simulate assembly using simulate_assembly. "
                "User specified: \"{args}\". "
                "Parse the method (gibson or restriction_ligation) and any enzyme names, "
                "using the current sequence as the insert fragment."
            ),
        ),
        Command(
            name="validate",
            description="Validate the current construct",
            usage="/validate",
            prompt_template=(
                "Validate the current plasmid construct using validate_plasmid. "
                "Use the sequence from the last assembly or search result in session. "
                "Report all warnings and whether it passed."
            ),
        ),
        Command(
            name="export",
            description="Export GenBank, FASTA, SVG map, primers CSV, and protocol",
            usage="/export <name>",
            prompt_template=(
                "Export all output files for the construct. "
                "Name it \"{args}\" (or 'pConstruct' if blank). "
                "Call validate_plasmid first if not already validated, "
                "then call export_files."
            ),
        ),
        Command(
            name="load",
            description="Load a sequence from a local file (.dna, .gb, .fa)",
            usage="/load <path>",
            prompt_template=(
                "Load the sequence from the local file at path \"{args}\" "
                "using import_sequence. Report what was loaded (name, length, topology)."
            ),
        ),
        Command(
            name="introduce-gene",
            description="End-to-end gene introduction: fetch CDS, optimise codons, suggest parts",
            usage="/introduce-gene <gene> in <source_organism> into <target_host> [goal: <goal>]",
            prompt_template=(
                "The user wants to introduce a gene into a host organism. "
                "Arguments: \"{args}\". "
                "Parse the gene name, source organism, target host (e_coli / yeast / plant_nuclear), "
                "and optional expression goal from the arguments. "
                "Then call introduce_gene with those values. "
                "Present the cassette description, recommended parts, and next steps clearly."
            ),
        ),
    ]
}

_HELP_COMMAND = Command(
    name="help",
    description="Show available slash commands",
    usage="/help",
    prompt_template="",  # not sent to agent — rendered directly
)


def parse_input(text: str) -> tuple[str | None, str]:
    """Return (command_name, args) if text starts with /, else (None, text).

    Returns (None, text) for plain messages so callers can pass them through unchanged.
    """
    text = text.strip()
    if not text.startswith("/"):
        return None, text
    parts = text[1:].split(None, 1)
    cmd_name = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""
    return cmd_name, args


def expand(cmd_name: str, args: str) -> str | None:
    """Expand a command into the agent prompt string.

    Returns None for /help (handled by the UI separately).
    Raises ValueError for unknown commands.
    """
    if cmd_name == "help":
        return None
    if cmd_name not in COMMANDS:
        known = ", ".join(f"/{c}" for c in sorted(COMMANDS))
        raise ValueError(f"Unknown command /{cmd_name}. Available: {known}")
    template = COMMANDS[cmd_name].prompt_template
    return template.format(args=args)


def help_markdown() -> str:
    """Render a compact command reference as Markdown."""
    lines = ["**Available commands**\n"]
    for cmd in COMMANDS.values():
        lines.append(f"`{cmd.usage}`  \n{cmd.description}")
    lines.append("`/help`  \nShow this message")
    return "\n\n".join(lines)
