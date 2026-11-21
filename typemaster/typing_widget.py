"""Python wrapper around the bidirectional typing-engine component.

All real-time behaviour (keystroke capture, live WPM, the countdown timer) runs
in the browser inside ``frontend/typing_engine/index.html``. Because it lives in
its own iframe, Streamlit reruns can never reset the timer. The component only
talks to Python once - when the test ends - by returning the typed text and the
elapsed time, which Python then re-scores on the server.
"""
from __future__ import annotations

from typing import Any, Optional

import streamlit.components.v1 as components

from . import config

_component = components.declare_component("typemaster_typing_engine", path=str(config.FRONTEND_DIR))


def typing_engine(
    *, text: str, duration: int, test_id: str, personal_best: Optional[float], key: str
) -> Optional[dict[str, Any]]:
    """Render the typing arena. Returns ``None`` until the test is finished."""
    return _component(
        text=text,
        duration=duration,
        test_id=test_id,
        personal_best=personal_best,
        key=key,
        default=None,
    )
