"""Bridge ConstructSession to Streamlit session_state."""
from __future__ import annotations

from typing import Any

from src.session.construct import ConstructSession


def session_from_state(state: Any) -> ConstructSession:
    """Build session from st.session_state or any dict-like mapping."""
    if isinstance(state, ConstructSession):
        return state
    if hasattr(state, "to_dict"):
        data = dict(state)
    else:
        data = dict(state)
    return ConstructSession.from_state_dict(data)


def apply_to_state(session: ConstructSession, state: Any) -> None:
    """Write ConstructSession back into session_state keys."""
    data = session.to_state_dict()
    for key, value in data.items():
        if value is not None:
            state[key] = value
        elif key in state:
            state[key] = value
