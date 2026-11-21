"""Analytics tab: summary cards, personal-best matrix and interactive charts."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import analytics, config, ui
from ..database import Database, DatabaseError, Player
from ..utils import format_seconds


def _best_matrix(history: pd.DataFrame) -> pd.DataFrame:
    pivot = history.pivot_table(index="duration_sec", columns="difficulty", values="wpm", aggfunc="max")
    pivot = pivot.reindex(index=list(config.DURATIONS), columns=list(config.DIFFICULTIES))
    pivot = pivot.apply(lambda col: col.map(lambda v: "--" if pd.isna(v) else f"{v:.0f}"))
    pivot.index = [f"{d} seconds" for d in pivot.index]
    pivot.index.name = "Test length"
    return pivot.reset_index()


def render(db: Database, player: Player) -> None:
    try:
        history = db.history(player.id)
        stats = db.stats(player.id)
    except DatabaseError as exc:
        ui.error_state("Analytics could not be loaded", f"{exc} Reload the page to try again.")
        return

    if history.empty:
        ui.empty_state(
            "No data to chart yet",
            "Finish a typing test and your speed, accuracy and consistency charts will appear here.",
        )
        return

    ui.card_grid([
        ui.card("Personal best", f"{stats['best_wpm']:.0f}", "WPM", "amber"),
        ui.card("Average speed", f"{stats['avg_wpm']:.1f}", "WPM"),
        ui.card("Average accuracy", f"{stats['avg_accuracy']:.1f}%", "", "mint"),
        ui.card("Total mistakes", str(int(stats["mistakes"])), f"over {format_seconds(stats['seconds'])} of typing", "coral"),
    ])

    ui.show_chart(analytics.wpm_trend_chart(history))
    if len(history) < 3:
        st.caption("Complete a few more tests to unlock the moving average.")

    left, right = st.columns(2)
    with left:
        ui.show_chart(analytics.accuracy_vs_wpm_chart(history))
    with right:
        ui.show_chart(analytics.difficulty_chart(history))
    left, right = st.columns(2)
    with left:
        ui.show_chart(analytics.duration_chart(history))
    with right:
        ui.show_chart(analytics.activity_chart(history))

    ui.section_title("Personal bests", "Best net WPM for every setup")
    ui.show_table(_best_matrix(history))
