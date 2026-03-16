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
    data = {
        "saved_at": ts,
        "name": first_user[:80] or "Conversation",
        "messages": serialisable_msgs,
        "last_sequence": session.get("last_sequence"),
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
        except Exception:
            pass
    return result


def _restore_conversation(filepath: str) -> None:
    """Load a saved conversation into session state."""
    data = json.loads(Path(filepath).read_text())
    st.session_state.messages = data.get("messages", [])
    if data.get("last_sequence"):
        st.session_state.last_sequence = data["last_sequence"]
    if data.get("last_validation"):
        st.session_state.last_validation = data["last_validation"]
    if data.get("last_optimization"):
        st.session_state.last_optimization = data["last_optimization"]


# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Crake",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
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

# ── Sidebar — saved conversations ────────────────────────────────────────────
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

if not messages:
    render_intro()
else:
    col_chat, col_data = st.columns([52, 48], gap="medium")

    with col_chat:
        chat_box = st.container(height=700, border=False)
        with chat_box:
            render_chat_history(messages)

        btn_clear, btn_save, btn_dl, _ = st.columns([2, 2, 2, 1])
        with btn_clear:
            if st.button("Clear", use_container_width=True):
                for k in _DEFAULTS:
                    st.session_state[k] = _DEFAULTS[k]
                st.rerun()
        with btn_save:
            user_msgs = [m for m in messages if m.get("role") == "user"]
            if user_msgs:
                if st.button("Save to history", use_container_width=True):
                    _save_conversation_to_disk(messages, st.session_state)
                    st.toast("Conversation saved!", icon="✅")
        with btn_dl:
            user_msgs2 = [m for m in messages if m.get("role") == "user"]
            if user_msgs2:
                md = _conversation_to_markdown(messages)
                fname = f"crake_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.md"
                st.download_button(
                    "Export .md",
                    data=md,
                    file_name=fname,
                    mime="text/markdown",
                    use_container_width=True,
                )

    with col_data:
        render_data_panel(
            sequence_result=st.session_state.last_sequence or {},
            optimization_result=st.session_state.last_optimization,
            seqviz_data=st.session_state.last_seqviz,
            primers_result=st.session_state.last_primers or {},
            validation_result=st.session_state.last_validation or {},
            export_paths=st.session_state.export_paths,
        )

# ── Chat input ───────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask Crake anything, or type /genesearch, /fetch, /load…")

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
                with st.spinner("Crake is thinking…"):
                    updated_history, tool_log = run_agent_turn(
                        user_message=agent_message,
                        conversation_history=st.session_state.messages,
                        session=st.session_state,
                    )

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
