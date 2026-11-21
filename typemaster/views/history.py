"""History tab: every saved test with filters, CSV export and a delete option."""
from __future__ import annotations

import streamlit as st

from .. import config, ui
from ..database import Database, DatabaseError, Player
from ..utils import to_local


def render(db: Database, player: Player) -> None:
    try:
        history = db.history(player.id)
    except DatabaseError as exc:
        ui.error_state("Your history could not be loaded", f"{exc} Reload the page to try again.")
        return

    if history.empty:
        ui.empty_state(
            "Nothing here yet",
            "Your completed tests are saved automatically. Take your first test to start your history.",
        )
        return

    left, right = st.columns(2)
    with left:
        duration = st.selectbox("Test length", ["All"] + list(config.DURATIONS), key="hist_duration",
                                format_func=lambda d: d if d == "All" else f"{d} seconds")
    with right:
        difficulty = st.selectbox("Difficulty", ["All"] + list(config.DIFFICULTIES), key="hist_difficulty")

    view = history
    if duration != "All":
        view = view[view["duration_sec"] == duration]
    if difficulty != "All":
        view = view[view["difficulty"] == difficulty]

    if view.empty:
        ui.empty_state("No tests match these filters", "Try a different length or difficulty.")
        return

    table = view.assign(
        when=to_local(view["created_at"]),
    )[["when", "mode", "duration_sec", "difficulty", "wpm", "accuracy", "raw_wpm",
       "correct_chars", "incorrect_chars", "elapsed_sec"]]
    table["mode"] = table["mode"].map({"standard": "Practice", "daily": "Daily", "drill": "Drill"})
    table.columns = ["Date", "Mode", "Length (s)", "Difficulty", "WPM", "Accuracy", "Raw WPM",
                     "Correct", "Mistakes", "Time (s)"]

    st.caption(f"{len(table)} of {len(history)} tests")
    ui.show_table(
        table,
        column_config={
            "Date": st.column_config.DatetimeColumn(format="MMM D, YYYY, h:mm a"),
            "WPM": st.column_config.NumberColumn(format="%.1f"),
            "Accuracy": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
            "Raw WPM": st.column_config.NumberColumn(format="%.1f"),
            "Time (s)": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    st.download_button(
        "Download as CSV", table.to_csv(index=False).encode("utf-8"),
        file_name=f"typemaster-history-{player.name.replace(' ', '_')}.csv", mime="text/csv",
        key="hist_download",
    )

    with st.expander("Delete my history"):
        st.write("This permanently removes all of your saved tests. Other players are not affected.")
        confirmed = st.checkbox("I understand this cannot be undone", key="hist_confirm_delete")
        if st.button("Delete all my tests", disabled=not confirmed, key="hist_delete_btn"):
            try:
                removed = db.delete_history(player.id)
            except DatabaseError as exc:
                st.error(str(exc))
            else:
                st.session_state.hist_confirm_delete = False
                st.toast(f"Deleted {removed} tests")
                st.rerun()
