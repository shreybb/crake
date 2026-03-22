"""Crake — AI-assisted plasmid design.

Run with:
    uv run streamlit run app.py
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path

import streamlit as st

from src.agent.commands import expand, help_markdown, parse_input
from src.agent.loop import run_agent_turn
from src.agent.tool_dispatch import _result_to_seqviz
from src.ui.components import (
    render_chat_history,
    render_data_panel,
    render_header,
    render_intro,
    render_sidebar_history,
)
from src.ui.styles import inject_css, inject_command_palette

# ── Conversation persistence ─────────────────────────────────────────────────
_SAVE_DIR = Path.home() / ".crake" / "conversations"
_SAVE_DIR.mkdir(parents=True, exist_ok=True)


def _conversation_to_markdown(messages: list[dict]) -> str:
    lines = [
        "# Crake — Saved Conversation",
        f"_Exported {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
    ]
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            continue
        if role == "user":
            lines += [f"**You:** {content}", ""]
        elif role == "assistant":
            lines += [f"**Crake:** {content}", ""]
    return "\n".join(lines)


def _save_conversation_to_disk(messages: list[dict], session) -> None:
    """Persist conversation + key session data to ~/.crake/conversations/."""
    first_user = next(
        (m["content"] for m in messages
         if m.get("role") == "user" and isinstance(m.get("content"), str)),
        "",
    )
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = first_user[:30].strip().replace(" ", "_").replace("/", "").replace("\\", "")
    filename = f"{ts}_{slug or 'conversation'}.json"
    serialisable_msgs = [
        m for m in messages if isinstance(m.get("content"), str)
    ]
    seqviz = session.get("last_seqviz")
    if seqviz is None and session.get("last_sequence"):
        seqviz = _result_to_seqviz(session["last_sequence"])
    data = {
        "saved_at": ts,
        "name": first_user[:80] or "Conversation",
        "messages": serialisable_msgs,
        "last_sequence": session.get("last_sequence"),
        "last_seqviz": seqviz,
        "last_validation": session.get("last_validation"),
        "last_optimization": session.get("last_optimization"),
    }
    (_SAVE_DIR / filename).write_text(json.dumps(data, indent=2, default=str))


def _load_saved_conversations() -> list[dict]:
    """Return list of saved conversation metadata, newest first."""
    files = sorted(_SAVE_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
    result = []
    for f in files[:30]:
        try:
            data = json.loads(f.read_text())
            result.append({
                "file": f,
                "name": data.get("name", f.stem),
                "saved_at": data.get("saved_at", ""),
            })
        except Exception as exc:
            import logging
            logging.warning("Failed to load saved conversation %s: %s", f, exc)
    return result


def _restore_conversation(filepath: str) -> None:
    """Load a saved conversation into session state."""
    data = json.loads(Path(filepath).read_text())
    st.session_state.messages = data.get("messages", [])
    if data.get("last_sequence"):
        st.session_state.last_sequence = data["last_sequence"]
    if data.get("last_seqviz"):
        st.session_state.last_seqviz = data["last_seqviz"]
    elif data.get("last_sequence"):
        # Rebuild seqviz from the raw sequence result if it wasn't saved
        st.session_state.last_seqviz = _result_to_seqviz(data["last_sequence"])
    if data.get("last_validation"):
        st.session_state.last_validation = data["last_validation"]
    if data.get("last_optimization"):
        st.session_state.last_optimization = data["last_optimization"]


# ── Tool status labels ───────────────────────────────────────────────────────

def _tool_status_label(name: str, inp: dict) -> str:
    """Return a human-readable description of a tool call for the status widget."""
    if name == "search_gene":
        gene = inp.get("gene_name", "")
        org = inp.get("organism", "")
        return f"🔍 Searching NCBI for **{gene}**" + (f" in *{org}*" if org else "")
    if name == "fetch_by_accession":
        return f"📥 Fetching accession **{inp.get('accession', '')}** from {inp.get('db', 'nucleotide')}"
    if name == "import_sequence":
        p = inp.get("path", "")
        return f"📂 Loading file **{Path(p).name if p else p}**"
    if name == "suggest_parts":
        return f"💡 Looking up parts for host **{inp.get('host', '')}**"
    if name == "optimize_codons":
        host = inp.get("host", "").replace("_", " ")
        return f"🔄 Codon-optimising for **{host}**"
    if name == "find_target_sites":
        method = inp.get("method", "")
        return f"🎯 Scanning for **{method}** target sites"
    if name == "design_primers":
        return f"🧪 Designing PCR primers (Tm {inp.get('opt_tm', 60):.0f} °C)"
    if name == "simulate_assembly":
        method = inp.get("method", "")
        frags = len(inp.get("fragments", []))
        return f"⚙️ Simulating **{method}** assembly with {frags} fragment(s)"
    if name == "validate_plasmid":
        return f"✅ Validating construct **{inp.get('name', 'construct')}**"
    if name == "export_files":
        return f"📦 Exporting files for **{inp.get('name', 'construct')}**"
    return f"🔧 Running **{name}**"


# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Crake",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
inject_command_palette()

# ── Session defaults ────────────────────────────────────────────────────────
_DEFAULTS: dict = {
    "messages": [],
    "last_sequence": None,
    "last_assembly": None,
    "last_validation": None,
    "last_primers": None,
    "last_optimization": None,
    "last_seqviz": None,
    "export_paths": {},
    "tool_calls_log": [],
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Sidebar — always render so the collapse toggle is always visible ──────────
conversations = _load_saved_conversations()
to_load = render_sidebar_history(conversations)
if to_load:
    _restore_conversation(to_load)
    st.rerun()

# ── Header ──────────────────────────────────────────────────────────────────
seq = st.session_state.last_sequence or {}
val = st.session_state.last_validation
render_header(
    gene_name=seq.get("gene_name"),
    gene_organism=seq.get("organism"),
    validation_valid=val.get("valid") if val else None,
    message_count=len([m for m in st.session_state.messages if m.get("role") == "user"]),
    tool_call_count=len(st.session_state.tool_calls_log),
)

# ── Main content ────────────────────────────────────────────────────────────
messages = st.session_state.messages
_typed_input = ""
_submitted = False

if not messages:
    render_intro()
    # Input on the intro page (full-width, no columns yet)
    with st.form("intro_chat_form", clear_on_submit=True):
        _ic1, _ic2 = st.columns([11, 1])
        with _ic1:
            _typed_input = st.text_input(
                "intro_msg",
                placeholder="Ask Crake anything, or type /genesearch, /fetch, /load…",
                label_visibility="collapsed",
            )
        with _ic2:
            _submitted = st.form_submit_button("↑", use_container_width=True)
else:
    col_chat, col_data = st.columns([48, 52], gap="small")

    with col_chat:
        # ── Chat window ──────────────────────────────────────────────────────
        st.markdown('<div class="crake-chat-win-header">Chat</div>', unsafe_allow_html=True)

        # Action bar
        user_msgs = [m for m in messages if m.get("role") == "user"]
        btn_clear, btn_save, btn_dl, _ = st.columns([2, 2, 3, 5])
        with btn_clear:
            if st.button("Clear", use_container_width=True):
                for k in _DEFAULTS:
                    st.session_state[k] = _DEFAULTS[k]
                st.rerun()
        with btn_save:
            if user_msgs and st.button("Save", use_container_width=True):
                _save_conversation_to_disk(messages, st.session_state)
                st.toast("Conversation saved!", icon="✅")
        with btn_dl:
            if user_msgs:
                md = _conversation_to_markdown(messages)
                fname = f"crake_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.md"
                st.download_button(
                    "Export",
                    data=md,
                    file_name=fname,
                    mime="text/markdown",
                    use_container_width=True,
                )

        # Scrollable messages area
        chat_box = st.container(height=580, border=False)
        with chat_box:
            render_chat_history(messages)

        # Input form — contained inside the chat window
        with st.form("chat_input_form", clear_on_submit=True):
            _ic1, _ic2 = st.columns([11, 1])
            with _ic1:
                _typed_input = st.text_input(
                    "chat_msg",
                    placeholder="Ask Crake anything, or type /genesearch, /fetch, /load…",
                    label_visibility="collapsed",
                )
            with _ic2:
                _submitted = st.form_submit_button("↑", use_container_width=True)

    with col_data:
        render_data_panel(
            sequence_result=st.session_state.last_sequence or {},
            optimization_result=st.session_state.last_optimization,
            seqviz_data=st.session_state.last_seqviz,
            primers_result=st.session_state.last_primers or {},
            validation_result=st.session_state.last_validation or {},
            export_paths=st.session_state.export_paths,
        )

user_input = _typed_input.strip() if (_submitted and _typed_input) else None

# ── Agent turn ───────────────────────────────────────────────────────────────
if user_input:
    cmd_name, args = parse_input(user_input)

    if cmd_name == "help":
        st.session_state.messages.append({"role": "user", "content": "/help"})
        st.session_state.messages.append({"role": "assistant", "content": help_markdown()})
        st.rerun()

    else:
        try:
            agent_message = expand(cmd_name, args) if cmd_name else user_input
        except ValueError as exc:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.messages.append({"role": "assistant", "content": str(exc)})
            st.rerun()
            agent_message = None

        if agent_message:
            try:
                with st.status("Crake is thinking…", expanded=True) as _agent_status:
                    def _on_tool(name: str, inp: dict) -> None:
                        _agent_status.write(_tool_status_label(name, inp))

                    updated_history, tool_log = run_agent_turn(
                        user_message=agent_message,
                        conversation_history=st.session_state.messages,
                        session=st.session_state,
                        on_tool_start=_on_tool,
                    )
                    _agent_status.update(label="Done", state="complete", expanded=False)

                for msg in updated_history:
                    if msg.get("role") == "user" and msg.get("content") == agent_message:
                        msg["content"] = user_input
                        break

                st.session_state.messages = updated_history
                st.session_state.tool_calls_log.extend(tool_log)
            except Exception as exc:
                st.session_state.messages.append({"role": "user", "content": user_input})
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Something went wrong: {exc}",
                })
            st.rerun()
