"""Session-state helpers so the rest of the app never touches raw keys."""
from __future__ import annotations

from typing import Optional

import streamlit as st

from .database import Player

_DEFAULTS = {
    "player": None,            # Player | None
    "phase": "idle",           # "idle" | "running" | "finished"
    "test": None,              # dict: id, text, duration, difficulty, pb
    "result": None,            # services.TestResult | None
    "submitted": None,         # set of test ids already processed
    "last_first": None,
    "booted": False,           # splash already shown this session
    "test_page": None,         # page a test was started on (leaving it cancels the test)
    "nav": "Home",        # (difficulty, passage index) of the previous challenge
}


def init_state() -> None:
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = set() if key == "submitted" else value


def get_player() -> Optional[Player]:
    return st.session_state.player


def set_player(player: Player) -> None:
    """Switch player and drop any test that belonged to the previous one."""
    st.session_state.player = player
    reset_test()


def reset_test() -> None:
    st.session_state.phase = "idle"
    st.session_state.test = None
    st.session_state.result = None
