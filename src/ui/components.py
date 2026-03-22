"""Streamlit rendering components for the Crake UI."""
from __future__ import annotations

import base64
import re
from pathlib import Path

_ACCESSION_RE = re.compile(r'^[A-Z]{1,3}\d{5,9}(\.\d+)?$')

import pandas as pd
import streamlit as st

try:
    from streamlit_seqviz import streamlit_seqviz as _seqviz_component
    _SEQVIZ_AVAILABLE = True
except ImportError:
    _SEQVIZ_AVAILABLE = False


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def _build_gene_pill_html(gene_name: str, gene_organism: str | None) -> str:
    if _ACCESSION_RE.match(gene_name):
        display = f"Accession {gene_name}"
    else:
        display = gene_name[:24] + ("…" if len(gene_name) > 24 else "")
    org_label = f" — {gene_organism}" if gene_organism else ""
    tip = f' title="{display}{org_label}"'
    return (
        f'<span class="crake-pill"{tip}>'
        f'<span class="crake-pip pip-blue"></span>{display}</span>'
    )


def _build_validation_pill_html(validation_valid: bool) -> str:
    if validation_valid:
        return (
            '<span class="crake-pill" title="All validation checks passed">'
            '<span class="crake-pip pip-green"></span>Validated</span>'
        )
    return (
        '<span class="crake-pill" title="Construct has validation warnings">'
        '<span class="crake-pip pip-amber"></span>Has warnings</span>'
    )


def _build_activity_html(message_count: int, tool_call_count: int) -> str:
    kbd_hint = (
        '<span class="crake-kbd-hint" title="Type / to see all commands">'
        '<kbd class="crake-kbd">/</kbd>'
        '<span class="crake-kbd-label">commands</span>'
        '</span>'
    )
    msgs = (
        f'<span class="crake-stat" title="{message_count} conversation turns">'
        f'<svg width="12" height="12" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" style="opacity:.45">'
        f'<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
        f'<span style="color:#3A7080;">{message_count}</span></span>'
    ) if message_count > 0 else ""
    tools = (
        f'<span class="crake-stat" title="{tool_call_count} tool calls made this session">'
        f'<svg width="12" height="12" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" style="opacity:.45">'
        f'<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77'
        f'a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91'
        f'a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>'
        f'<span style="color:#3A7080;">{tool_call_count}</span></span>'
    ) if tool_call_count > 0 else ""
    return kbd_hint + msgs + tools


def render_header(
    gene_name: str | None = None,
    gene_organism: str | None = None,
    validation_valid: bool | None = None,
    message_count: int = 0,
    tool_call_count: int = 0,
) -> None:
    """Sticky top bar: wordmark + live status pills + session stats."""
    pills_html = ""
    if gene_name:
        pills_html += _build_gene_pill_html(gene_name, gene_organism)
    if validation_valid is not None:
        pills_html += _build_validation_pill_html(validation_valid)

    stats_html = _build_activity_html(message_count, tool_call_count)

    st.markdown(
        f'<div class="crake-header">'
        f'  <div class="crake-logo-wrap">'
        f'    <div class="crake-logo-mark">🧬</div>'
        f'    <span class="crake-wordmark">Cra<b>ke</b></span>'
        f'  </div>'
        f'  <div class="crake-header-status">{pills_html}</div>'
        f'  <div class="crake-header-stats">{stats_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Intro page
# ---------------------------------------------------------------------------

_STEPS = [
    ("01", "🔍", "Find a Gene",
     "Search NCBI by natural language, fetch by accession, or load a local SnapGene / GenBank / FASTA file.",
     "/genesearch GFP Aequorea victoria"),
    ("02", "🧩", "Design the Construct",
     "Get vector backbone, promoter, terminator, and selectable marker suggestions matched to your host.",
     "/suggest agrobacterium"),
    ("03", "⚗️", "Optimize & Edit",
     "Codon-optimise for your expression host, find CRISPR PAM sites, restriction targets, and design PCR primers.",
     "/optimize plant_nuclear"),
    ("04", "📦", "Validate & Export",
     "Check ORFs, GC windows, and restriction map. Export annotated GenBank, FASTA, SVG map, CSV, and a protocol.",
     "/export pMyConstruct"),
]

_EXAMPLES = [
    ("Aquatic plant glow", "/genesearch find an aquatic plant we can easily edit to glow"),
    ("Fetch by accession", "/fetch U55762"),
    ("CRISPR in tobacco", "/genesearch rbcL Nicotiana tabacum"),
    ("Load a file", "/load /path/to/plasmid.dna"),
]


_COMMANDS_TABLE = [
    ("/genesearch &lt;query&gt;",  "Find a gene sequence by natural language or species name"),
    ("/fetch &lt;accession&gt;",   "Retrieve a sequence directly by NCBI accession"),
    ("/load &lt;path&gt;",         "Import a local .dna, .gb, or .fasta file"),
    ("/suggest &lt;host&gt;",      "Get vector backbone and part recommendations for a host"),
    ("/targets &lt;method&gt;",    "Find CRISPR PAM sites or restriction enzyme cut sites"),
    ("/optimize &lt;host&gt;",     "Codon-optimise the loaded sequence for expression"),
    ("/primers [fwd] [rev]",       "Design PCR primers, optionally with overhangs"),
    ("/assemble &lt;method&gt;",   "Simulate Gibson or restriction-ligation assembly"),
    ("/validate",                  "Check ORFs, GC content, and restriction map"),
    ("/export &lt;name&gt;",       "Write GenBank, FASTA, SVG map, CSV, and protocol"),
]


def render_intro() -> None:
    """Minimal, uniform welcome screen shown before any conversation starts."""
    rows = "".join(
        f'<tr>'
        f'<td class="cmd-key">{cmd}</td>'
        f'<td class="cmd-desc">{desc}</td>'
        f'</tr>'
        for cmd, desc in _COMMANDS_TABLE
    )
    st.markdown(
        '<div class="crake-intro-wrap">'
        '  <div class="crake-intro-glow"></div>'
        '  <div class="crake-intro-hero">'
        '    <div class="crake-intro-title"><span>Crake</span></div>'
        '    <p class="crake-intro-sub">'
        '      AI-assisted plasmid design. From sequence discovery to a lab-ready construct.'
        '    </p>'
        '  </div>'
        f'  <table class="crake-cmd-table">{rows}</table>'
        '  <div class="crake-intro-footer" style="margin-top:32px;">'
        '    <span>Type a command above, or describe what you want in plain English</span>'
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Command hints (compact, shown in chat panel)
# ---------------------------------------------------------------------------

_HINT_COMMANDS = [
    ("/genesearch", "find a gene by natural language"),
    ("/fetch", "retrieve by accession number"),
    ("/load", "import .dna / .gb / .fasta file"),
    ("/suggest", "recommend parts for a host"),
    ("/targets", "find CRISPR / restriction sites"),
    ("/optimize", "codon-optimise for a host"),
    ("/primers", "design PCR primers"),
    ("/assemble", "simulate Gibson or restriction-ligation"),
    ("/validate", "check the current construct"),
    ("/export", "write all output files"),
]


def render_command_hints() -> None:
    """Compact command reference shown below the empty chat."""
    rows = "".join(
        f'<tr>'
        f'<td style="padding:6px 18px 6px 0;white-space:nowrap;vertical-align:middle;">'
        f'<code style="background:rgba(0,229,160,0.06);border:1px solid rgba(0,229,160,0.14);'
        f'border-radius:5px;padding:3px 9px;font-size:12px;color:#00E5A0;'
        f'font-family:Fira Code,JetBrains Mono,monospace;display:inline-block;">{cmd}</code></td>'
        f'<td style="padding:6px 0;font-size:13px;color:#3A7080;vertical-align:middle;">{desc}</td>'
        f'</tr>'
        for cmd, desc in _HINT_COMMANDS
    )
    st.markdown(
        f'<div class="crake-cmd-wrap">'
        f'<div class="crake-cmd-label">Commands</div>'
        f'<table style="border-collapse:collapse;width:100%;table-layout:auto;">'
        f'{rows}</table>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_sidebar_history(conversations: list[dict]) -> str | None:
    """Render saved conversations in the sidebar. Returns file path to load, or None."""
    st.sidebar.markdown(
        '<div class="crake-sb-title">Saved conversations</div>',
        unsafe_allow_html=True,
    )

    if not conversations:
        st.sidebar.markdown(
            '<div class="crake-sb-empty">No saved conversations yet.<br>'
            'Use <b>Save chat</b> in the main view.</div>',
            unsafe_allow_html=True,
        )
        return None

    to_load = None
    for convo in conversations:
        name = convo.get("name", "Conversation")[:50]
        saved_at = convo.get("saved_at", "")
        # Format date nicely
        try:
            dt = __import__("datetime").datetime.strptime(saved_at, "%Y%m%d_%H%M%S")
            date_label = dt.strftime("%b %d, %H:%M")
        except Exception:
            date_label = saved_at[:16]

        st.sidebar.markdown(
            f'<div class="crake-sb-item-name" title="{name}">{name}</div>'
            f'<div class="crake-sb-item-meta">{date_label}</div>',
            unsafe_allow_html=True,
        )
        if st.sidebar.button("Load →", key=f"load_{convo['file']}", use_container_width=True):
            to_load = str(convo["file"])

        st.sidebar.markdown('<div style="height:1px;background:#112030;margin:8px 0;"></div>', unsafe_allow_html=True)

    return to_load


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

def render_chat_history(messages: list[dict]) -> None:
    """Render the conversation as styled chat bubbles."""
    if not messages:
        st.markdown(
            '<div class="crake-chat-empty">'
            '<div class="crake-chat-empty-icon">🧬</div>'
            '<div class="crake-chat-empty-text">Your conversation will appear here</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if isinstance(content, list) and content and isinstance(content[0], dict):
            if content[0].get("type") == "tool_result":
                continue

        if role == "user" and isinstance(content, str):
            st.markdown(
                f'<div class="crake-msg-user-row">'
                f'  <div class="crake-role-user">You</div>'
                f'  <div class="crake-msg-user">{content}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        elif role == "assistant":
            text = _extract_text(content)
            tool_badges = _extract_tool_badges(content)
            if text or tool_badges:
                badges_html = "".join(
                    f'<span class="crake-tool-badge">⚙ {b}</span>'
                    for b in tool_badges
                )
                separator = "<br>" if badges_html and text else ""
                st.markdown(
                    f'<div class="crake-msg-ai-row">'
                    f'  <div class="crake-role-ai">Crake</div>'
                    f'  <div class="crake-msg-ai">{badges_html}{separator}{text}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if hasattr(block, "type") and block.type == "text":
                parts.append(block.text)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return " ".join(parts)
    return ""


def _extract_tool_badges(content) -> list[str]:
    if not isinstance(content, list):
        return []
    names = []
    for block in content:
        if hasattr(block, "type") and block.type == "tool_use":
            names.append(block.name)
        elif isinstance(block, dict) and block.get("type") == "tool_use":
            names.append(block.get("name", ""))
    return names


# ---------------------------------------------------------------------------
# Data panel (tabs wrapper)
# ---------------------------------------------------------------------------

def _render_top_viewer(seqviz_data: dict | None, export_paths: dict) -> None:
    """Render the interactive seqviz component or SVG fallback at the top of the data panel."""
    has_seqviz = bool(seqviz_data and seqviz_data.get("seq") and _SEQVIZ_AVAILABLE)
    has_svg = bool(export_paths.get("map") and Path(export_paths["map"]).exists())

    if has_seqviz:
        _seqviz_component(
            name=seqviz_data["name"],
            seq=seqviz_data["seq"],
            annotations=seqviz_data["annotations"],
            style={"height": "280px", "background": "#070D15", "borderRadius": "10px", "padding": "4px"},
            highlights=[],
            enzymes=["EcoRI", "PstI", "BamHI", "HindIII", "NcoI", "NotI", "XhoI"],
        )
        st.markdown(
            '<div style="margin-bottom:2px;font-size:11px;color:#3A7080;text-align:right;'
            'padding-right:4px;">Hover over features · scroll to zoom · click to select</div>',
            unsafe_allow_html=True,
        )
    elif has_svg:
        svg_data = Path(export_paths["map"]).read_text()
        b64 = base64.b64encode(svg_data.encode()).decode()
        st.markdown(
            f'<div style="text-align:center;padding:8px 0;">'
            f'<img src="data:image/svg+xml;base64,{b64}" '
            f'style="max-width:100%;border-radius:10px;background:#070D15;padding:8px;">'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        _empty_state("Load a sequence to see the interactive map here.", "🗺️")


def render_data_panel(
    sequence_result: dict,
    optimization_result: dict | None,
    seqviz_data: dict | None,
    primers_result: dict,
    validation_result: dict,
    export_paths: dict,
) -> None:
    """Render the right-hand data panel: seqviz viewer at top, then tabs."""
    _render_top_viewer(seqviz_data, export_paths)
    st.markdown('<div style="margin-top:4px"></div>', unsafe_allow_html=True)

    tab_seq, tab_primers, tab_val, tab_dl = st.tabs(
        ["Sequence", "Primers", "Validation", "Downloads"]
    )
    render_sequence(sequence_result, tab_seq, optimization_result=optimization_result)
    render_primers(primers_result, tab_primers)
    render_validation(validation_result, tab_val)
    render_downloads(export_paths, tab_dl)


# ---------------------------------------------------------------------------
# Sequence tab
# ---------------------------------------------------------------------------

def _render_optimization_metrics(optimization_result: dict) -> None:
    """Render the codon-optimisation before/after metrics row."""
    gc_before = optimization_result["gc_before"]
    gc_after = optimization_result["gc_after"]
    delta = round(gc_after - gc_before, 1)
    st.markdown('<div style="margin-top:12px"></div>', unsafe_allow_html=True)
    o1, o2, o3 = st.columns(3)
    o1.metric("GC Before Optim.", f"{gc_before:.1f}%",
              help="GC content before codon optimisation")
    o2.metric("GC After Optim.", f"{gc_after:.1f}%", delta=f"{delta:+.1f}%",
              help="GC content after optimisation — closer to 50% is generally better")
    o3.metric("Optimised Host",
              optimization_result.get("host", "—").replace("_", " ").title(),
              help="Host organism whose codon table was used for optimisation")


def _render_gene_info(sequence_result: dict) -> None:
    """Render the name + organism row."""
    st.markdown(
        '<div style="margin:16px 0 8px;">'
        '<span style="font-size:11px;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.1em;color:#3A7080;">Gene info</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    organism = sequence_result.get("organism", "—")
    organism_url = "https://www.ncbi.nlm.nih.gov/taxonomy?term=" + organism.replace(" ", "+")
    i1, i2 = st.columns(2)
    i1.markdown(
        f'<span style="font-size:11.5px;color:#3A7080;text-transform:uppercase;'
        f'letter-spacing:.06em;font-weight:600;">Name</span><br>'
        f'<span style="font-size:15px;color:#C8E8F0;font-weight:500;">'
        f'{sequence_result.get("gene_name", "—")}</span>',
        unsafe_allow_html=True,
    )
    i2.markdown(
        f'<span style="font-size:11.5px;color:#3A7080;text-transform:uppercase;'
        f'letter-spacing:.06em;font-weight:600;">Organism</span><br>'
        f'<a href="{organism_url}" target="_blank" rel="noopener" '
        f'style="font-size:15px;color:#C8E8F0;font-style:italic;text-decoration:none;'
        f'border-bottom:1px dashed #3A7080;transition:color .15s;" '
        f'title="View on NCBI Taxonomy">{organism}</a>',
        unsafe_allow_html=True,
    )


def render_sequence(
    sequence_result: dict,
    tab,
    optimization_result: dict | None = None,
) -> None:
    with tab:
        if not sequence_result:
            _empty_state("No sequence loaded yet.", "🔬")
            return

        seq = sequence_result.get("sequence", "")
        gc = round((seq.count("G") + seq.count("C")) / len(seq) * 100, 1) if seq else 0.0
        host = sequence_result.get("suggested_host", "—").replace("_", " ").title()

        c1, c2, c3 = st.columns(3)
        c1.metric("Length", f"{len(seq):,} bp",
                  help="Total base pairs in the loaded sequence")
        c2.metric("GC Content", f"{gc:.1f}%",
                  help="Percentage of G+C bases. Typical range 40–60%; extremes reduce expression")
        c3.metric("Recommended Host", host,
                  help="Suggested cloning/expression host inferred from the source organism")

        if optimization_result and "gc_before" in optimization_result:
            _render_optimization_metrics(optimization_result)

        _render_gene_info(sequence_result)

        if seq:
            seq_type = sequence_result.get("sequence_type", "")
            type_label = f" · {seq_type}" if seq_type else ""
            st.markdown(
                f'<div style="margin-top:16px;font-size:11px;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:0.1em;color:#3A7080;margin-bottom:8px;">Sequence preview '
                f'<span style="font-weight:400;text-transform:none;letter-spacing:0;">'
                f'(first 600 bp{type_label})</span></div>',
                unsafe_allow_html=True,
            )
            st.code(seq[:600] + ("…" if len(seq) > 600 else ""), language=None)

        if note := sequence_result.get("note"):
            st.info(note)


# ---------------------------------------------------------------------------
# Plasmid map tab
# ---------------------------------------------------------------------------

def render_plasmid_map(
    map_svg_path: str | None,
    tab,
    seqviz_data: dict | None = None,
) -> None:
    with tab:
        has_seqviz = bool(seqviz_data and seqviz_data.get("seq") and _SEQVIZ_AVAILABLE)
        has_svg    = bool(map_svg_path and Path(map_svg_path).exists())

        if not has_seqviz and not has_svg:
            _empty_state(
                "Load a sequence or run <code>/export</code> to view the plasmid map.",
                "🗺️",
            )
            return

        if has_seqviz:
            _seqviz_component(
                name=seqviz_data["name"],
                seq=seqviz_data["seq"],
                annotations=seqviz_data["annotations"],
                style={
                    "height": "500px",
                    "background": "#ffffff",
                    "borderRadius": "10px",
                    "padding": "8px",
                },
                highlights=[],
                enzymes=["EcoRI", "PstI", "BamHI", "HindIII", "NcoI", "NotI", "XhoI"],
            )

        if has_svg:
            if has_seqviz:
                st.markdown(
                    '<div style="margin-top:16px;font-size:11px;font-weight:700;'
                    'text-transform:uppercase;letter-spacing:.1em;color:#3A7080;">'
                    'Annotated map (static)</div>',
                    unsafe_allow_html=True,
                )
            svg_data = Path(map_svg_path).read_text()
            b64 = base64.b64encode(svg_data.encode()).decode()
            st.markdown(
                f'<div style="text-align:center;padding:12px 0;">'
                f'<img src="data:image/svg+xml;base64,{b64}" '
                f'style="max-width:660px;width:100%;border-radius:10px;'
                f'background:#070D15;padding:8px;">'
                f'</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Primers tab
# ---------------------------------------------------------------------------

def render_primers(primers_result: dict, tab) -> None:
    with tab:
        pairs = primers_result.get("primer_pairs", [])
        if not pairs:
            _empty_state("No primers designed yet.", "🧪")
            return

        rows = []
        for pair in pairs:
            for direction in ("forward", "reverse"):
                p = pair.get(direction, {})
                rows.append({
                    "Pair": pair.get("rank", 0) + 1,
                    "Direction": direction.capitalize(),
                    "Sequence": p.get("full_sequence") or p.get("binding_region", ""),
                    "Tm (°C)": p.get("tm_celsius", "—"),
                    "GC %": p.get("gc_percent", "—"),
                    "Length": p.get("length", "—"),
                })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        overhangs = primers_result.get("overhangs_applied", {})
        if overhangs.get("forward") or overhangs.get("reverse"):
            st.caption(
                f"Overhangs — fwd: `{overhangs.get('forward', '—')}` "
                f"rev: `{overhangs.get('reverse', '—')}`"
            )


# ---------------------------------------------------------------------------
# Validation tab
# ---------------------------------------------------------------------------

def render_validation(validation_result: dict, tab) -> None:
    with tab:
        if not validation_result:
            _empty_state("No validation run yet.", "✅")
            return

        warnings = validation_result.get("warnings", [])
        valid = validation_result.get("valid", False)

        if valid:
            st.success("Construct passed all validation checks")
        elif warnings:
            for w in warnings:
                st.warning(w)
        else:
            st.info("Validation complete")

        gc = validation_result.get("gc_analysis", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Length", f"{validation_result.get('length_bp', 0):,} bp")
        c2.metric("Overall GC", f"{gc.get('overall_gc_percent', 0):.1f}%")
        c3.metric("ORFs found", len(validation_result.get("orfs", [])))

        flagged = gc.get("flagged_windows", [])
        if flagged:
            st.markdown(
                '<div style="margin-top:16px;font-size:11px;font-weight:700;text-transform:uppercase;'
                'letter-spacing:.1em;color:#3A7080;margin-bottom:8px;">GC by Window</div>',
                unsafe_allow_html=True,
            )
            df_gc = pd.DataFrame(flagged)[["start", "gc_percent"]].rename(
                columns={"start": "Position (bp)", "gc_percent": "GC %"}
            )
            st.bar_chart(df_gc.set_index("Position (bp)"), color="#00E5A0")

        sites = validation_result.get("restriction_sites", [])
        if sites:
            st.markdown(
                '<div style="margin-top:16px;font-size:11px;font-weight:700;text-transform:uppercase;'
                'letter-spacing:.1em;color:#3A7080;margin-bottom:8px;">Restriction Sites</div>',
                unsafe_allow_html=True,
            )
            st.dataframe(
                pd.DataFrame(sites[:20])[["enzyme", "count"]],
                use_container_width=True,
                hide_index=True,
            )


# ---------------------------------------------------------------------------
# Downloads tab
# ---------------------------------------------------------------------------

def render_downloads(export_paths: dict, tab) -> None:
    with tab:
        if not export_paths:
            _empty_state(
                "Files appear here after running <code>/export</code>.",
                "📁",
            )
            return

        for label, key in [
            ("GenBank (.gb)", "genbank"),
            ("FASTA (.fa)", "fasta"),
            ("Primers CSV", "primers_csv"),
            ("Protocol (.md)", "protocol"),
            ("Plasmid Map (.svg)", "map"),
        ]:
            path = export_paths.get(key)
            if path and Path(path).exists():
                st.download_button(
                    label=f"⬇  {label}",
                    data=Path(path).read_bytes(),
                    file_name=Path(path).name,
                    use_container_width=True,
                )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _empty_state(message: str, icon: str = "·") -> None:
    st.markdown(
        f'<div style="padding:40px 24px;text-align:center;">'
        f'<div style="font-size:32px;margin-bottom:10px;opacity:.3;">{icon}</div>'
        f'<p style="color:#3A7080;font-size:13.5px;margin:0;">{message}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
