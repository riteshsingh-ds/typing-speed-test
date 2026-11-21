"""Practice page: choose a length and difficulty, then type."""
from __future__ import annotations

import streamlit as st

from .. import config, ui
from ..database import Database, DatabaseError, Player
from ..passages import DIFFICULTY_BLURBS
from . import arena


def _start() -> None:
    """Start button callback: read the *live* widget values, not values frozen at render time."""
    ss = st.session_state
    duration = ss.get("cfg_duration_widget", ss.get("cfg_duration_value", 60))
    difficulty = ss.get("cfg_difficulty_widget", ss.get("cfg_difficulty_value", "Medium"))
    arena.launch(difficulty, duration)


def stat_cards(db: Database, player: Player) -> None:
    try:
        s = db.stats(player.id)
    except DatabaseError as exc:
        ui.error_state("Your stats could not be loaded", str(exc))
        return
    if s["tests"] == 0:
        ui.card_grid([ui.card("Personal best", "--", "No tests yet", "amber"), ui.card("Average speed", "--", "WPM"),
                      ui.card("Average accuracy", "--"), ui.card("Tests taken", "0")])
        return
    ui.card_grid([
        ui.card("Personal best", f"{s['best_wpm']:.0f}", "WPM", "amber"),
        ui.card("Average speed", f"{s['avg_wpm']:.0f}", f"WPM, last 10 tests: {s['recent_wpm']:.0f}"),
        ui.card("Average accuracy", f"{s['avg_accuracy']:.1f}%", f"Best {s['best_accuracy']:.1f}%", "mint"),
        ui.card("Tests taken", str(s["tests"]), f"{s['mistakes']} mistakes in total"),
    ])


def render(db: Database, player: Player) -> None:
    if arena.active():
        arena.render(db, player)
        return
    ui.page_header("Practice", "Pick a length and difficulty. The timer starts on your first keystroke.")
    stat_cards(db, player)
    left, right = st.columns(2)
    with left:
        duration = ui.choice("Test length", config.DURATIONS, key="cfg_duration", default=60,
                             format_func=lambda d: f"{d} seconds")
    with right:
        difficulty = ui.choice("Difficulty", config.DIFFICULTIES, key="cfg_difficulty", default="Medium")
    best_text = ""
    try:
        best = db.personal_best(player.id, duration, difficulty)
        if best:
            best_text = f" Your best here: {best['wpm']:.0f} WPM at {best['accuracy']:.0f}% accuracy."
    except DatabaseError:
        pass
    st.caption(DIFFICULTY_BLURBS[difficulty] + best_text)
    ui.call_stretch(st.button, "Start test", type="primary", key="start_btn", on_click=_start)
