"""Progress page: level, streaks, badges and full test history."""
from __future__ import annotations

from datetime import date

import streamlit as st

from .. import ui
from ..database import Database, DatabaseError, Player
from ..progress import ACHIEVEMENTS, level_info, practice_days, streaks, total_xp, unlocked_ids
from . import history as history_view


def render(db: Database, player: Player) -> None:
    try:
        history = db.history(player.id)
    except DatabaseError as exc:
        ui.error_state("Your progress could not be loaded", str(exc))
        return
    ui.page_header("Progress", f"{player.name}'s level, streaks, badges and every test you have taken.")
    if history.empty:
        ui.empty_state("Your journey starts here",
                       "Finish a test to earn XP, start a streak and unlock your first badge.")
        ui.call_stretch(st.button, "Take a test", type="primary", key="prog_go", on_click=ui.go, args=("Practice",))
        return

    info = level_info(total_xp(history))
    current, best = streaks(practice_days(history))
    unlocked = unlocked_ids(history)
    ui.html_block(
        f'<div class="tm-level"><div class="tm-level-badge">{info.level}</div><div class="tm-level-body">'
        f'<div class="tm-level-title">{ui.esc(info.title)}</div>'
        f'<div class="tm-xpbar"><i style="width:{info.progress * 100:.0f}%"></i></div>'
        f'<div class="tm-sub" style="color:var(--muted);font-size:.85rem">{info.xp - info.floor} / {info.ceiling - info.floor} XP to level {info.level + 1} '
        f'&middot; {info.xp} XP total</div></div></div>'
    )
    ui.card_grid([
        ui.card("Current streak", f"{current}", "days in a row", "amber"),
        ui.card("Best streak", f"{best}", "days", "mint"),
        ui.card("Badges", f"{len(unlocked)}/{len(ACHIEVEMENTS)}", "unlocked"),
    ], cols=3)
    if current == 0:
        st.caption("Your streak is at zero. Finish any test today to start a new one.")
    elif date.today() not in practice_days(history):
        st.caption("Practice today to keep your streak alive.")

    ui.call_stretch(st.button, "Open Rewards: badges and certificates", key="prog_rewards", on_click=ui.go, args=("Rewards",))

    ui.section_title("Test history")
    history_view.render(db, player)
