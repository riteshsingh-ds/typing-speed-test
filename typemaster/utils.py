"""Small helpers shared by several modules."""
from __future__ import annotations

from datetime import datetime

import pandas as pd


def to_local(series: pd.Series) -> pd.Series:
    """Convert a UTC datetime Series to naive local time for display."""
    if series.empty:
        return series
    local_tz = datetime.now().astimezone().tzinfo
    return series.dt.tz_convert(local_tz).dt.tz_localize(None)


def format_seconds(total: float) -> str:
    """Format seconds as ``1h 05m``, ``12m 30s`` or ``45s``."""
    total = int(round(total))
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


def board_labels(board: pd.DataFrame, me_id: int | None = None, mark_me: bool = True) -> list[str]:
    """Display names for a leaderboard. Duplicate names get ``#id`` so players stay distinguishable."""
    if board.empty:
        return []
    counts = board["player"].str.lower().value_counts()
    labels = []
    for name, pid in zip(board["player"], board["player_id"]):
        label = f"{name} #{pid}" if counts[name.lower()] > 1 else name
        if mark_me and me_id is not None and pid == me_id:
            label += " (you)"
        labels.append(label)
    return labels
