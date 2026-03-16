"""Subprocess-based agent loop — uses the local `claude` CLI.

No separate Anthropic API key needed.  Authentication is handled by the
existing Claude Code session.

The loop uses ReAct-style tool calling:
  Claude responds with a <tool_call> XML block → we dispatch it → send
  the result back → repeat until Claude produces plain text.
"""
from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from src.agent.tool_definitions import TOOL_DEFINITIONS
from src.agent.tool_dispatch import dispatch

MAX_ITERATIONS = 10   # safety cap on tool-call rounds per turn
SUBPROCESS_TIMEOUT = 120  # seconds

# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _tool_docs() -> str:
    """Render tool definitions as a readable text block for the prompt."""
    lines: list[str] = []
    for t in TOOL_DEFINITIONS:
        props = t["input_schema"].get("properties", {})
        required = set(t["input_schema"].get("required", []))
        args = [
            f"    {n}{'*' if n in required else '?'}: "
            f"{s.get('type','any')} — {s.get('description', '')}"
            for n, s in props.items()
        ]
        lines.append(f"• {t['name']}: {t['description']}")
        lines.extend(args)
    return "\n".join(lines)


_SYSTEM = f"""\
You are Crake, an AI-assisted plasmid design assistant.
Help molecular biologists design DNA constructs: search for gene sequences,
optimise codons, design primers, simulate assembly, and validate constructs.

Guidelines:
- Be concise and scientific.
- Always call validate_plasmid before export_files.
- For plant / Agrobacterium work use host="agrobacterium".
- If a tool returns an error, explain it and suggest an alternative.

AVAILABLE TOOLS
{_tool_docs()}

TOOL CALL FORMAT
When you need to use a tool, respond with ONLY this block — nothing else:
<tool_call>
{{"name": "tool_name", "input": {{"arg1": "value1"}}}}
</tool_call>
I will run the tool and return the result. Then continue your reasoning.
When you are done with all tool calls, reply in plain text.
"""


def _build_prompt(history: list[dict]) -> str:
    """Render the full conversation history as a single text prompt."""
    parts = [_SYSTEM, "\n--- CONVERSATION ---\n"]

    for msg in history:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        parts.append(f"[Tool result]: {block.get('content', '')}")
            else:
                parts.append(f"User: {content}")

        elif role == "assistant":
            if isinstance(content, list):
                for block in content:
                    btype = block.type if hasattr(block, "type") else block.get("type", "")
                    if btype == "text":
                        text = block.text if hasattr(block, "text") else block.get("text", "")
                        if text:
                            parts.append(f"Crake: {text}")
                    elif btype == "tool_use":
                        name = block.name if hasattr(block, "name") else block.get("name", "")
                        inp = block.input if hasattr(block, "input") else block.get("input", {})
                        parts.append(
                            f"<tool_call>\n{json.dumps({'name': name, 'input': inp})}\n</tool_call>"
                        )
            else:
                parts.append(f"Crake: {content}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Claude subprocess call
# ---------------------------------------------------------------------------

_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


def _call_claude(prompt: str) -> str:
    """Run `claude -p` with the prompt on stdin and return the text result."""
    proc = subprocess.run(
        [
            "claude", "-p",
            "--output-format", "json",
            "--no-session-persistence",
        ],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude process error: {proc.stderr.strip()}")
    data = json.loads(proc.stdout)
    return data.get("result", "")


def _parse_tool_call(text: str) -> dict[str, Any] | None:
    m = _TOOL_CALL_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Public agent turn
# ---------------------------------------------------------------------------

def run_agent_turn(
    user_message: str,
    conversation_history: list[dict],
    session: dict,
    api_key: str = "",   # unused — kept for interface compatibility
) -> tuple[list[dict], list[dict]]:
    """Run one full agentic turn via the claude CLI subprocess.

    Args:
        user_message: Text the user typed.
        conversation_history: Mutable list of message dicts — updated in place.
        session: Mutable session dict (e.g. st.session_state) for tool side effects.
        api_key: Ignored. Kept so callers don't need to change signature.

    Returns:
        (conversation_history, tool_calls_log)
    """
    history = list(conversation_history)
    history.append({"role": "user", "content": user_message})
    tool_calls_log: list[dict] = []

    for _ in range(MAX_ITERATIONS):
        prompt = _build_prompt(history)
        response_text = _call_claude(prompt)

        tool_call = _parse_tool_call(response_text)

        if tool_call is None:
            # Final plain-text answer
            history.append({"role": "assistant", "content": response_text})
            break

        name = tool_call.get("name", "")
        inp = tool_call.get("input", {})

        try:
            result = dispatch(name, inp, session)
        except Exception as exc:
            result = {"error": str(exc)}

        tool_calls_log.append({"tool_name": name, "result": result})

        # Record the tool call and result in history for next iteration
        call_id = f"tu_{len(tool_calls_log)}"
        history.append({
            "role": "assistant",
            "content": [{"type": "tool_use", "id": call_id, "name": name, "input": inp}],
        })
        history.append({
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": call_id, "content": json.dumps(result)}],
        })

    conversation_history.clear()
    conversation_history.extend(history)
    return conversation_history, tool_calls_log


def extract_text_response(conversation_history: list[dict]) -> str:
    """Return the last assistant text from the conversation history."""
    for msg in reversed(conversation_history):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", [])
        if isinstance(content, str):
            return content
        for block in content:
            if hasattr(block, "type") and block.type == "text":
                return block.text
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "")
    return ""
