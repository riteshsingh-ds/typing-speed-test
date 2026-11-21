"""Key Doctor: finds the keys you miss and builds a drill around them."""
from __future__ import annotations

import streamlit as st

from .. import config, ui
from ..database import Database, DatabaseError, Player
from ..drills import build_drill
from ..progress import key_stats, weak_keys
from . import arena


def _start(weak) -> None:
    duration = st.session_state.get("drill_len_widget", 30)
    arena.launch("Medium", duration, build_drill(weak, duration), "drill")


def render(db: Database, player: Player) -> None:
    if arena.active():
        arena.render(db, player)
        return
    ui.page_header("Key Doctor", "Your personal weak-key report and a drill built from your own mistakes.")
    try:
        aggregate = db.key_stats(player.id)
    except DatabaseError as exc:
        ui.error_state("Key Doctor could not load your data", str(exc))
        return

    if not aggregate:
        ui.empty_state("No keystroke data yet",
                       "Finish a test in Practice or Daily. Key Doctor then maps every key you type and shows where you slip.")
        ui.call_stretch(st.button, "Go to Practice", key="kd_go_practice", on_click=ui.go, args=("Practice",))
        return

    weak = weak_keys(aggregate)
    typed_keys = len(key_stats(aggregate))
    ui.card_grid([
        ui.card("Keys mapped", str(typed_keys), "distinct keys typed"),
        ui.card("Weakest key", weak[0].key.upper() if weak else "--",
                f"{weak[0].rate:.0%} missed" if weak else "No weak keys yet", "coral" if weak else "mint"),
        ui.card("Keys to fix", str(len(weak)), f"need {config.MIN_KEY_ATTEMPTS}+ attempts to count"),
    ], cols=3)

    ui.html_block('<div class="tm-legend"><span>Clean</span><i></i><span>Often missed</span></div>')
    ui.html_block(ui.keyboard_html(aggregate))
    st.caption("Counts every mistake you made, including ones you corrected. Hover a key for details.")

    if not weak:
        st.success("No weak keys detected. Keep practising and Key Doctor will keep watching.")
        return

    ui.section_title("Your weakest keys")
    ui.card_grid([ui.card(w.key.upper(), f"{w.rate:.0%}", f"{w.errors} of {w.attempts} missed", "coral") for w in weak[:4]],
                 cols=4)
    ui.choice("Drill length", (30, 60), key="drill_len", default=30, format_func=lambda d: f"{d} seconds")
    ui.call_stretch(st.button, "Start my drill", type="primary", key="drill_start_btn", on_click=_start, args=(weak,))
