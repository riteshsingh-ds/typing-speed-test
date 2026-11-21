"""Daily Challenge: one text for every player, one board per day."""
from __future__ import annotations

from datetime import date

import streamlit as st

from .. import config, ui
from ..database import Database, DatabaseError, Player
from ..passages import daily_challenge
from ..utils import board_labels
from . import arena


def _start() -> None:
    day = date.today()
    arena.launch(config.DAILY_DIFFICULTY, config.DAILY_DURATION, daily_challenge(day).text, "daily", day.isoformat())


def render(db: Database, player: Player) -> None:
    if arena.active():
        arena.render(db, player)
        return
    today = date.today()
    ui.page_header("Daily Challenge", f"{today.strftime('%A, %B %d')}. Everyone types the same text. One board per day.")
    try:
        mine = db.daily_best(player.id, today.isoformat())
        board = db.daily_leaderboard(today.isoformat(), 10)
    except DatabaseError as exc:
        ui.error_state("The daily challenge could not be loaded", str(exc))
        return

    ui.card_grid([
        ui.card("Today's setup", f"{config.DAILY_DURATION}s", config.DAILY_DIFFICULTY, "amber"),
        ui.card("Your best today", f"{mine['wpm']:.0f}" if mine else "--", f"{mine['accuracy']:.1f}% accuracy" if mine else "Not attempted yet", "mint" if mine else ""),
        ui.card("Players today", str(len(board)), "on the board"),
    ], cols=3)
    label = "Beat your score" if mine else "Start today's challenge"
    ui.call_stretch(st.button, label, type="primary", key="daily_start_btn", on_click=_start)

    ui.section_title("Today's board")
    if board.empty:
        ui.empty_state("Nobody has played yet", "Set the first score of the day and own the top spot.")
        return
    table = board.assign(
        Rank=[{1: "1st", 2: "2nd", 3: "3rd"}.get(i, f"{i}th") for i in range(1, len(board) + 1)],
        Player=board_labels(board, player.id),
    )[["Rank", "Player", "wpm", "accuracy"]]
    table.columns = ["Rank", "Player", "WPM", "Accuracy"]
    ui.show_table(table, column_config={
        "WPM": st.column_config.NumberColumn(format="%.1f"),
        "Accuracy": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
    })
