"""Home page: product landing, community pulse, your day and feature tour."""
from __future__ import annotations

from datetime import date

import streamlit as st

from .. import config, ui
from ..database import Database, DatabaseError, Player
from ..progress import level_info, practice_days, streaks, total_xp

FEATURES = (
    ("Daily Challenge", "Same text for everyone, a fresh board every day. Build a streak and climb the ranks."),
    ("Key Doctor", "Maps every key you type, shows a keyboard heat-map and builds drills around the keys you miss."),
    ("Ghost pace", "Every result is plotted against your previous best run, second by second."),
    ("XP, levels and badges", "Clean typing earns more XP than fast sloppy typing. Unlock 15 badges as you improve."),
    ("Real analytics", "Speed trends, accuracy vs speed, difficulty and length breakdowns, all from your own data."),
    ("Share your score", "Download a polished result card for every test and post it anywhere."),
)
STEPS = (
    ("01", "Pick a mode", "Practice at your own pace or take today's challenge."),
    ("02", "Type with live feedback", "Green for right, red for wrong. WPM and accuracy update on every key."),
    ("03", "Improve with data", "Key Doctor, ghost pace and streaks show exactly what to fix next."),
)


def render(db: Database, player: Player) -> None:
    try:
        community = db.platform_stats(date.today().isoformat())
        history = db.history(player.id)
    except DatabaseError as exc:
        ui.error_state("The home page could not load its data", str(exc))
        return

    if community["top_player"]:
        top_rows = (f'<div class="tm-mini"><span>Fastest player</span><b>{ui.esc(community["top_player"])}</b></div>'
                    f'<div class="tm-mini"><span>Top speed</span><b>{community["top_wpm"]:.0f} WPM</b></div>')
    else:
        top_rows = '<div class="tm-mini"><span>No scores yet. Be the first on the board.</span></div>'
    ui.html_block(
        f'<div class="tm-hero"><div class="tm-hero-main">'
        f'<div class="tm-eyebrow">Welcome back, {ui.esc(player.name)}</div>'
        f'<h1>Type faster. <em>Type cleaner.</em> Every single day.</h1>'
        f'<p>TypeMaster is the typing trainer that finds your weak keys, races your own best run and keeps you coming back with daily challenges.</p>'
        f'<div class="tm-demo"><span class="ok">Speed is just rhythm you </span><span class="bad">l</span>'
        f'<span class="ok">earned to repeat</span><span class="caret"></span></div></div>'
        f'<div class="tm-hero-side"><h4>Community pulse</h4>'
        f'<div class="tm-mini"><span>Tests completed</span><b>{community["tests"]}</b></div>'
        f'<div class="tm-mini"><span>Players</span><b>{community["players"]}</b></div>'
        f'<div class="tm-mini"><span>Playing today\'s challenge</span><b>{community["daily_players"]}</b></div>{top_rows}</div></div>'
    )

    c1, c2, c3 = st.columns([1, 1, 1.3])
    with c1:
        ui.call_stretch(st.button, "Start practicing", type="primary", key="home_practice", on_click=ui.go, args=("Practice",))
    with c2:
        ui.call_stretch(st.button, "Today's challenge", key="home_daily", on_click=ui.go, args=("Daily",))
    with c3:
        ui.call_stretch(st.button, "Open Key Doctor", key="home_doctor", on_click=ui.go, args=("Key Doctor",))

    if not history.empty:
        ui.section_title("Your day")
        info = level_info(total_xp(history))
        current, best = streaks(practice_days(history))
        try:
            done = db.daily_best(player.id, date.today().isoformat())
        except DatabaseError:
            done = None
        ui.card_grid([
            ui.card("Level", str(info.level), info.title, "amber"),
            ui.card("Day streak", str(current), f"Best: {best} days", "mint"),
            ui.card("Today's challenge", f"{done['wpm']:.0f} WPM" if done else "Open", "Completed" if done else "Not played yet"),
        ], cols=3)

    ui.section_title("What makes TypeMaster different")
    ui.html_block('<div class="tm-features">' + "".join(
        f'<div class="tm-feature"><span class="tag">{ui.esc(i + 1):0>2}</span><h4>{ui.esc(t)}</h4><p>{ui.esc(b)}</p></div>'
        for i, (t, b) in enumerate(FEATURES)) + "</div>")

    ui.section_title("How it works")
    ui.html_block('<div class="tm-steps">' + "".join(
        f'<div class="tm-step"><span class="n">{n}</span><h4>{ui.esc(t)}</h4><p>{ui.esc(b)}</p></div>' for n, t, b in STEPS) + "</div>")

    ui.html_block(
        f'<div class="tm-footer"><div><b>{config.APP_NAME}</b> &middot; {config.APP_TAGLINE}</div>'
        f'<div>{config.FOUNDER_TITLE}: <b>{ui.esc(config.FOUNDER_NAME)}</b></div></div>'
    )
