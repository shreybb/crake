"""Execute slash commands by calling tool dispatch directly (no LLM)."""
from __future__ import annotations

import json
import re
from typing import Any

from src.agent.tool_dispatch import dispatch
from src.tools.gene_introduction import _VALID_HOSTS

_UNIPROT_RE = re.compile(r"^[OPQ][0-9][A-Z0-9]{3}[0-9](?:-\d+)?$", re.IGNORECASE)
_HOST_ALIASES = {
    "e.coli": "e_coli",
    "ecoli": "e_coli",
    "e_coli": "e_coli",
    "yeast": "yeast",
    "s.cerevisiae": "yeast",
    "plant": "plant_nuclear",
    "plant_nuclear": "plant_nuclear",
    "agrobacterium": "agrobacterium",
    "agro": "agrobacterium",
}


def _normalize_host(raw: str) -> str:
    key = raw.strip().lower().replace(" ", "_").replace("-", "_")
    if key in _HOST_ALIASES:
        return _HOST_ALIASES[key]
    if key in _VALID_HOSTS:
        return key
    raise ValueError(
        f"Unknown host {raw!r}. Use one of: {', '.join(sorted(_VALID_HOSTS))}"
    )


def _session_sequence(session: dict) -> tuple[str, dict]:
    data = session.get("last_sequence") or {}
    seq = data.get("sequence", "")
    if not seq or data.get("error"):
        raise ValueError(
            "No sequence loaded. Use `/genesearch`, `/fetch`, `/load`, or **Introduce a Gene** first."
        )
    return seq, data


def _parse_genesearch(args: str) -> dict[str, Any]:
    text = args.strip()
    if not text:
        raise ValueError("Usage: `/genesearch <gene> in <organism>` — e.g. `/genesearch GFP in Aequorea victoria`")
    if re.search(r"\s+in\s+", text, flags=re.IGNORECASE):
        gene, organism = re.split(r"\s+in\s+", text, maxsplit=1, flags=re.IGNORECASE)
        return {"gene_name": gene.strip(), "organism": organism.strip()}
    parts = text.split()
    if len(parts) < 2:
        raise ValueError(
            "Usage: `/genesearch <gene> in <organism>` or `/genesearch GFP Aequorea victoria`"
        )
    return {"gene_name": parts[0], "organism": " ".join(parts[1:])}


def _parse_introduce_gene(args: str) -> dict[str, Any]:
    text = args.strip()
    expression_goal = ""
    goal_match = re.search(r"\bgoal\s*:\s*(.+)$", text, flags=re.IGNORECASE)
    if goal_match:
        expression_goal = goal_match.group(1).strip()
        text = text[: goal_match.start()].strip()

    if not re.search(r"\s+into\s+", text, flags=re.IGNORECASE):
        raise ValueError(
            "Usage: `/introduce-gene <gene> in <organism> into <host> [goal: <goal>]`"
        )
    left, host_raw = re.split(r"\s+into\s+", text, maxsplit=1, flags=re.IGNORECASE)
    target_host = _normalize_host(host_raw.strip().split()[0])

    if not re.search(r"\s+in\s+", left, flags=re.IGNORECASE):
        raise ValueError("Include source organism: `... in <organism> into <host>`")
    gene_name, source_organism = re.split(
        r"\s+in\s+", left, maxsplit=1, flags=re.IGNORECASE
    )
    gene_name = gene_name.strip()
    source_organism = source_organism.strip()
    if not gene_name:
        raise ValueError("Gene name is required.")
    return {
        "gene_name": gene_name,
        "source_organism": source_organism or "unknown",
        "target_host": target_host,
        "expression_goal": expression_goal,
    }


def introduce_gene_input(
    gene_name: str,
    source_organism: str,
    target_host: str,
    expression_goal: str = "",
) -> dict[str, Any]:
    """Build introduce_gene tool input from structured form fields."""
    return _parse_introduce_gene(
        f"{gene_name.strip()} in {source_organism.strip()} into {target_host}"
        + (f" goal: {expression_goal}" if expression_goal else "")
    )


def _build_tool_input(cmd_name: str, args: str, session: dict) -> tuple[str, dict[str, Any]]:
    text = args.strip()

    if cmd_name == "genesearch":
        return "search_gene", _parse_genesearch(text)

    if cmd_name == "fetch":
        if not text:
            raise ValueError("Usage: `/fetch <accession>`")
        acc = text.split()[0]
        if _UNIPROT_RE.match(acc):
            return "fetch_by_accession", {"accession": acc, "db": "uniprot"}
        return "fetch_by_accession", {"accession": acc, "db": "nucleotide"}

    if cmd_name == "load":
        if not text:
            raise ValueError("Usage: `/load <path>`")
        return "import_sequence", {"path": text.split()[0]}

    if cmd_name == "suggest":
        if not text:
            raise ValueError("Usage: `/suggest <host>` — e.g. `/suggest yeast`")
        return "suggest_parts", {"host": _normalize_host(text.split()[0])}

    if cmd_name == "optimize":
        if not text:
            raise ValueError("Usage: `/optimize <host>`")
        seq, _ = _session_sequence(session)
        return "optimize_codons", {"sequence": seq, "host": _normalize_host(text.split()[0])}

    if cmd_name == "targets":
        if not text:
            raise ValueError(
                "Usage: `/targets <crispr|restriction|homologous> ...` — "
                "crispr: optional PAM (e.g. TTTV); homologous: position required"
            )
        parts = text.split()
        method = parts[0].lower()
        seq, seq_data = _session_sequence(session)
        inp: dict[str, Any] = {
            "sequence": seq,
            "method": method,
            "topology": seq_data.get("topology", "linear"),
        }
        if method == "homologous":
            if len(parts) < 2:
                raise ValueError("Usage: `/targets homologous <position>`")
            inp["position"] = int(parts[1])
        elif method == "crispr" and len(parts) >= 2:
            inp["pam"] = parts[1]
        return "find_target_sites", inp

    if cmd_name == "primers":
        seq, _ = _session_sequence(session)
        parts = text.split()
        inp = {"template": seq}
        if len(parts) >= 1:
            inp["overhang_fwd"] = parts[0]
        if len(parts) >= 2:
            inp["overhang_rev"] = parts[1]
        return "design_primers", inp

    if cmd_name == "assemble":
        if not text:
            raise ValueError(
                "Usage: `/assemble gibson <other_fragment>` or "
                "`/assemble restriction_ligation <enzyme> [<enzyme2> ...] <other_fragment>`"
            )
        parts = text.split()
        method = parts[0].lower()
        if method not in ("gibson", "restriction_ligation"):
            raise ValueError("Method must be `gibson` or `restriction_ligation`.")
        seq, _ = _session_sequence(session)
        if method == "gibson":
            if len(parts) < 2:
                raise ValueError(
                    "Gibson assembly needs two fragments. "
                    "Example: `/assemble gibson backbone.fa` (uses the loaded sequence as the insert)."
                )
            return "simulate_assembly", {
                "method": "gibson",
                "fragments": [seq, parts[1]],
            }
        if len(parts) < 3:
            raise ValueError(
                "Usage: `/assemble restriction_ligation <enzyme> [<enzyme2>] <other_fragment>`"
            )
        return "simulate_assembly", {
            "method": "restriction_ligation",
            "fragments": [seq, parts[-1]],
            "enzymes": parts[1:-1],
        }

    if cmd_name == "validate":
        seq, seq_data = _session_sequence(session)
        name = seq_data.get("gene_name") or seq_data.get("accession") or "construct"
        topology = seq_data.get("topology", "circular")
        if topology not in ("circular", "linear"):
            topology = "circular"
        return "validate_plasmid", {
            "sequence": seq,
            "name": name,
            "topology": topology,
        }

    if cmd_name == "export":
        name = text.split()[0] if text else "pConstruct"
        seq, seq_data = _session_sequence(session)
        if not session.get("last_validation"):
            dispatch(
                "validate_plasmid",
                {
                    "sequence": seq,
                    "name": name,
                    "topology": seq_data.get("topology", "circular"),
                },
                session,
            )
        prior_asm = session.get("last_assembly") or {}
        if not prior_asm.get("success"):
            session["last_assembly"] = {
                "product_sequence": seq,
                "topology": seq_data.get("topology", "circular"),
                "method": "direct",
                "success": True,
            }
        return "export_files", {"name": name}

    if cmd_name == "introduce-gene":
        return "introduce_gene", _parse_introduce_gene(text)

    raise ValueError(f"Unhandled command: {cmd_name}")


def format_result_message(tool_name: str, result: dict[str, Any]) -> str:
    """Turn a tool result dict into a short assistant message."""
    if result.get("error"):
        return f"**Error:** {result['error']}"

    if tool_name == "search_gene":
        return (
            f"**{result.get('gene_name', 'Gene')}** from *{result.get('organism', '?')}* — "
            f"{result.get('length_bp', len(result.get('sequence', '')))} bp loaded into the viewer."
        )

    if tool_name == "fetch_by_accession":
        if result.get("sequence_type") == "protein":
            return (
                f"Fetched **{result.get('accession')}** (protein, {result.get('length_aa')} aa). "
                "Codon optimisation requires a nucleotide CDS — use `/genesearch` or a nucleotide accession."
            )
        return (
            f"Fetched **{result.get('accession')}** — "
            f"{result.get('length_bp', 0)} bp, suggested host `{result.get('suggested_host')}`."
        )

    if tool_name == "import_sequence":
        return (
            f"Loaded **{result.get('gene_name', 'sequence')}** "
            f"({result.get('length_bp', 0)} bp, {result.get('topology', 'unknown')} topology)."
        )

    if tool_name == "suggest_parts":
        bb = result.get("recommended_backbones") or result.get("backbones") or []
        names = [b.get("name", "?") for b in bb[:3]]
        return f"Part suggestions for host — top backbones: {', '.join(names) or 'see panel'}."

    if tool_name == "optimize_codons":
        opt = result.get("optimized_sequence", "")
        return (
            f"Codon optimisation complete — {len(opt)} bp "
            f"(GC {result.get('gc_after', '?')}%). See optimisation metrics in the data panel."
        )

    if tool_name == "find_target_sites":
        n = result.get("site_count", len(result.get("target_sites", [])))
        rec = result.get("recommended_site")
        extra = f" Recommended: `{rec}`." if rec else ""
        return f"Found **{n}** {result.get('method', '')} site(s).{extra}"

    if tool_name == "design_primers":
        pairs = result.get("primer_pairs", [])
        return f"Designed **{len(pairs)}** primer pair(s). See the Primers tab."

    if tool_name == "simulate_assembly":
        if not result.get("success"):
            return f"Assembly failed: {result.get('error', 'unknown error')}"
        return (
            f"**{result.get('method')}** assembly — "
            f"{result.get('product_length_bp')} bp {result.get('topology')} product."
        )

    if tool_name == "validate_plasmid":
        status = "passed" if result.get("passed_checks") else "has warnings"
        warns = result.get("warnings", [])
        tail = f"\n\nWarnings:\n" + "\n".join(f"- {w}" for w in warns[:8]) if warns else ""
        return f"Validation **{status}** for `{result.get('name', 'construct')}`.{tail}"

    if tool_name == "introduce_gene":
        return (
            f"**{result.get('gene')}** → `{result.get('target_host')}`\n\n"
            f"{result.get('cassette_description', '')}\n\n"
            f"Optimised CDS: {len(result.get('optimized_sequence', ''))} bp. "
            f"Vector: **{result.get('recommended_backbone', {}).get('name', '?')}**."
        )

    if tool_name == "export_files":
        lines = ["Exported files:"]
        for key, path in result.items():
            if not key.endswith("_error"):
                lines.append(f"- `{key}`: {path}")
        return "\n".join(lines)

    return f"```json\n{json.dumps(result, indent=2)[:2000]}\n```"


def execute_command(cmd_name: str, args: str, session: dict) -> tuple[str, str, dict[str, Any]]:
    """Run a slash command. Returns ``(tool_name, user_message, result)``."""
    tool_name, tool_input = _build_tool_input(cmd_name, args, session)
    result = dispatch(tool_name, tool_input, session)
    message = format_result_message(tool_name, result)
    return tool_name, message, result
