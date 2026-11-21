"""3-second branded boot screen shown once per session while the app warms up."""
from __future__ import annotations

import time

import streamlit as st

from . import config
from .database import Database, DatabaseError


def show(load_database) -> Database | None:
    """Show the splash, do the real start-up work inside it, then clear it.

    ``load_database`` is called while the splash is visible. Returns the database (or ``None``
    when it could not be opened; the caller renders the error state).
    """
    seconds = config.SPLASH_SECONDS
    holder = st.empty()
    started = time.monotonic()
    if seconds > 0:
        holder.markdown(
            f'<div class="tm-splash" style="--splash:{seconds}s;--step:{seconds / 3:.2f}s"><div class="tm-splash-inner">'
            f'<div class="tm-logo big">TM</div><div class="tm-splash-title">{config.APP_NAME}</div>'
            f'<div class="tm-splash-tag">{config.APP_TAGLINE}</div>'
            '<div class="tm-splash-bar"><i></i></div>'
            '<div class="tm-splash-steps"><span>Connecting to your database</span>'
            '<span>Loading passages and daily challenge</span><span>Preparing leaderboard</span></div></div>'
            f'<div class="tm-splash-by">{config.FOUNDER_TITLE} <b>{config.FOUNDER_NAME}</b></div></div>',
            unsafe_allow_html=True,
        )
    db = None
    try:
        db = load_database()
        db.platform_stats()  # warm the connection / page cache for the home screen
    except DatabaseError:
        db = None
    remaining = seconds - (time.monotonic() - started)
    if remaining > 0:
        time.sleep(remaining)
    holder.empty()
    return db
