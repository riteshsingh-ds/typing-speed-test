"""Leaderboard tab: each player's best result, ranked by WPM."""
from __future__ import annotations

import streamlit as st

from datetime import date

from .. import config, ui
from ..database import Database, DatabaseError, Player
from ..utils import to_local

_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def render(db: Database, player: Player) -> None:
    ui.page_header("Leaderboard", "Each player's single best result, ranked by speed.")
    board_kind = ui.choice("Board", ("All time", "Today's challenge"), key="lb_board", default="All time")
    if board_kind == "Today's challenge":
        _daily(db, player)
        return
    left, right = st.columns(2)
    with left:
        duration = st.selectbox("Test length", ["All"] + list(config.DURATIONS), key="lb_duration",
                                format_func=lambda d: d if d == "All" else f"{d} seconds")
    with right:
        difficulty = st.selectbox("Difficulty", ["All"] + list(config.DIFFICULTIES), key="lb_difficulty")

    try:
        board = db.leaderboard(
            None if duration == "All" else duration,
            None if difficulty == "All" else difficulty,
        )
    except DatabaseError as exc:
        ui.error_state("The leaderboard could not be loaded", f"{exc} Reload the page to try again.")
        return

    if board.empty:
        ui.empty_state(
            "No scores on the board",
            "Nobody has set a score for this setup yet. Finish a test to take first place.",
            
        )
        return

    top = board.head(3)
    podium = []
    for rank, row in enumerate(top.itertuples(index=False), start=1):
        you = " (you)" if row.player.lower() == player.name.lower() else ""
        podium.append(
            f'<div class="tm-card"><div class="tm-medal">{_MEDALS[rank]}</div>'
            f'<div class="tm-name">{ui.esc(row.player + you)}</div>'
            f'<div class="tm-value" style="color:var(--amber)">{row.wpm:.0f}</div>'
            f'<div class="tm-sub">WPM at {row.accuracy:.1f}% accuracy</div></div>'
        )
    ui.html_block(f'<div class="tm-podium">{"".join(podium)}</div>')

    table = board.assign(
        Rank=[_MEDALS.get(i, str(i)) for i in range(1, len(board) + 1)],
        Player=[p + (" (you)" if p.lower() == player.name.lower() else "") for p in board["player"]],
        Setup=[f"{d} sec, {diff}" for d, diff in zip(board["duration_sec"], board["difficulty"])],
        Date=to_local(board["created_at"]),
    )[["Rank", "Player", "wpm", "accuracy", "Setup", "Date"]]
    table.columns = ["Rank", "Player", "WPM", "Accuracy", "Setup", "Date"]

    ui.show_table(
        table,
        column_config={
            "WPM": st.column_config.NumberColumn(format="%.1f"),
            "Accuracy": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
            "Date": st.column_config.DatetimeColumn(format="MMM D, YYYY"),
        },
    )
    st.caption(f"Top {len(board)} players, each ranked by their single best result.")


def _daily(db: Database, player: Player) -> None:
    try:
        board = db.daily_leaderboard(date.today().isoformat())
    except DatabaseError as exc:
        ui.error_state("The leaderboard could not be loaded", f"{exc} Reload the page to try again.")
        return
    if board.empty:
        ui.empty_state("No scores today", "Take the Daily Challenge to set the first score.")
        return
    table = board.assign(
        Rank=[_MEDALS.get(i, str(i)) for i in range(1, len(board) + 1)],
        Player=[p + (" (you)" if p.lower() == player.name.lower() else "") for p in board["player"]],
    )[["Rank", "Player", "wpm", "accuracy"]]
    table.columns = ["Rank", "Player", "WPM", "Accuracy"]
    ui.show_table(table, column_config={
        "WPM": st.column_config.NumberColumn(format="%.1f"),
        "Accuracy": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
    })
