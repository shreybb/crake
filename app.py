"""Crake — plasmid design workbench (deterministic tools, no LLM required).

Run with:
    uv run streamlit run app.py
"""
from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import datetime
import json
import os
import re
from pathlib import Path

import streamlit as st

from src.agent.command_runner import (
    execute_command,
    format_result_message,
    introduce_gene_input,
)
from src.agent.commands import help_markdown, parse_input, validate_command
from src.agent.tool_dispatch import _result_to_seqviz, dispatch
from src.session.construct import WorkflowStage
from src.session.streamlit_adapter import session_from_state
from src.ui.components import (
    render_chat_history,
    render_data_panel,
    render_header,
    render_intro,
    render_sidebar_gene_launcher,
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
    cs = session_from_state(session)
    data = {
        "saved_at": ts,
        "name": first_user[:80] or "Conversation",
        "messages": serialisable_msgs,
        **cs.to_state_dict(),
        "last_seqviz": seqviz or cs.seqviz,
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
    if data.get("last_assembly"):
        st.session_state.last_assembly = data["last_assembly"]
    if data.get("last_annotation"):
        st.session_state.last_annotation = data["last_annotation"]
    if data.get("last_primers"):
        st.session_state.last_primers = data["last_primers"]
    if data.get("export_paths"):
        st.session_state.export_paths = data["export_paths"]


# ── Supported hosts for pre-flight validation ──────────────────────────────
_UNSUPPORTED_HOST_RE = re.compile(
    r'\b(hansenula|aspergillus|trichoderma|bacillus\s+subtilis'
    r'|lactobacillus|streptomyces|neurospora|candida\s+albicans|fusarium)\b',
    re.IGNORECASE,
)

_HOST_SUPPORT_MSG = (
    "⚠️ **Unsupported host detected.** Crake currently supports:\n\n"
    "- **E. coli** — bacterial expression\n"
    "- **Yeast / S. cerevisiae** — fungal expression "
    "(Pichia, Kluyveromyces, and other non-cerevisiae yeasts are treated using "
    "S. cerevisiae protocols as a starting point)\n"
    "- **Plant nuclear** — Agrobacterium-mediated T-DNA delivery\n\n"
    "The pipeline will fall back to the closest supported host. "
    "For best results, use one of the supported hosts above."
)

_NO_LLM_HINT = (
    "Crake runs **slash commands** and the sidebar **Introduce a Gene** form — "
    "there is no free-text chat model. Type `/help` for commands."
)

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
    "last_annotation": None,
    "last_seqviz": None,
    "export_paths": {},
    "tool_calls_log": [],
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Sidebar — always render so the collapse toggle is always visible ──────────
intro_req = render_sidebar_gene_launcher()
if intro_req:
    st.session_state.pending_introduce_gene = intro_req
    st.rerun()

conversations = _load_saved_conversations()
to_load = render_sidebar_history(conversations)
if to_load:
    _restore_conversation(to_load)
    st.rerun()

# ── Header ──────────────────────────────────────────────────────────────────
seq = st.session_state.last_sequence or {}
val = st.session_state.last_validation
_cs = session_from_state(st.session_state)
_workflow = _cs.workflow_stage()
render_header(
    gene_name=seq.get("gene_name"),
    gene_organism=seq.get("organism"),
    validation_valid=val.get("passed_checks") if val else None,
    workflow_stage=_workflow.value if _workflow != WorkflowStage.EMPTY else None,
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
                placeholder="Type a slash command (/help, /genesearch, /fetch, /load…)",
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
            render_chat_history(messages, validation_result=st.session_state.last_validation)

        # Input form — contained inside the chat window
        with st.form("chat_input_form", clear_on_submit=True):
            _ic1, _ic2 = st.columns([11, 1])
            with _ic1:
                _typed_input = st.text_input(
                    "chat_msg",
                    placeholder="Type a slash command (/help, /genesearch, /fetch, /load…)",
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
            annotation_result=st.session_state.last_annotation or {},
            export_paths=st.session_state.export_paths,
        )

_pending_intro = st.session_state.pop("pending_introduce_gene", None)
user_input = _pending_intro or (_typed_input.strip() if (_submitted and _typed_input) else None)

# ── Command execution (no LLM) ───────────────────────────────────────────────
if user_input:
    if _UNSUPPORTED_HOST_RE.search(user_input):
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": _HOST_SUPPORT_MSG})
        st.rerun()

    if isinstance(_pending_intro, dict):
        display_input = (
            f"/introduce-gene {_pending_intro['gene_name']} in "
            f"{_pending_intro['source_organism']} into {_pending_intro['target_host']}"
        )
        cmd_name, args = "introduce-gene", ""
        tool_input = introduce_gene_input(
            _pending_intro["gene_name"],
            _pending_intro["source_organism"],
            _pending_intro["target_host"],
            _pending_intro.get("expression_goal", ""),
        )
    else:
        display_input = user_input
        cmd_name, args = parse_input(user_input)

    if cmd_name is None:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": _NO_LLM_HINT})
        st.rerun()

    if cmd_name == "help":
        st.session_state.messages.append({"role": "user", "content": "/help"})
        st.session_state.messages.append({"role": "assistant", "content": help_markdown()})
        st.rerun()

    try:
        validate_command(cmd_name)
        with st.spinner("Running…"):
            if isinstance(_pending_intro, dict):
                tool_name = "introduce_gene"
                result = dispatch(tool_name, tool_input, st.session_state)
                message = format_result_message(tool_name, result)
            else:
                tool_name, message, result = execute_command(
                    cmd_name, args, st.session_state
                )
        st.session_state.messages.append({"role": "user", "content": display_input})
        st.session_state.messages.append({"role": "assistant", "content": message})
        st.session_state.tool_calls_log.append({"tool_name": tool_name, "result": result})
    except ValueError as exc:
        st.session_state.messages.append({"role": "user", "content": display_input})
        st.session_state.messages.append({"role": "assistant", "content": str(exc)})
    except Exception as exc:
        st.session_state.messages.append({"role": "user", "content": display_input})
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Something went wrong: {exc}",
        })
    st.rerun()
