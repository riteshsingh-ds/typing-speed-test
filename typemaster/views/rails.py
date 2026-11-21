"""Left and right side rails: live, useful panels that fill the wide layout."""
from __future__ import annotations

from datetime import date

import streamlit as st

from .. import config, ui
from ..database import Database, DatabaseError, Player
from ..progress import (BY_ID, earned_dates, level_info, next_streak_goal, practice_days, streaks, total_xp)
from . import arena

TIPS = (
    "Keep your eyes on the text, not the keyboard. Looking down breaks your rhythm.",
    "Accuracy first. Speed follows once mistakes stop slowing you down.",
    "Rest your fingers on the home row (ASDF JKL;) and return there after every key.",
    "Type in a steady rhythm. Even pacing beats bursts of speed followed by errors.",
    "Use the correct finger for each key. Shortcuts feel faster today and cap your speed later.",
    "Short daily sessions beat one long weekly session. Five focused minutes count.",
    "Do not rush to fix every typo mid-word. Finish the word, then correct.",
    "Relax your shoulders and wrists. Tension slows your fingers and tires your hands.",
    "Read one word ahead while you type the current one.",
    "Use Key Doctor weekly. Fixing your two weakest keys lifts your whole average.",
    "Take the Daily Challenge: the same text every day shows your real progress.",
    "Sit upright with your forearms level with the keyboard.",
    "Slow down on purpose for one test. Clean, slow typing builds muscle memory.",
    "Numbers and symbols are the hardest. Practice Hard difficulty a little each week.",
)


def _quick_start() -> None:
    ui.go("Practice")
    arena.launch("Medium", 60)


def left(db: Database, player: Player) -> None:
    with st.container(key="rail_left"):
        try:
            history = db.history(player.id)
            daily = db.daily_best(player.id, date.today().isoformat())
        except DatabaseError:
            return
        xp = total_xp(history)
        info = level_info(xp)
        current, _ = streaks(practice_days(history))
        goal = next_streak_goal(current)
        ui.html_block(
            f'<div class="tm-rcard"><div class="tm-ravatar">{ui.esc(player.name[:1].upper())}</div>'
            f'<div class="tm-rname">{ui.esc(player.name)}</div>'
            f'<div class="tm-rsub">Level {info.level}, {ui.esc(info.title)}</div>'
            f'<div class="tm-xpbar"><i style="width:{info.progress * 100:.0f}%"></i></div>'
            f'<div class="tm-rsub">{info.xp - info.floor} / {info.ceiling - info.floor} XP to next level</div></div>'
        )
        ui.html_block(
            f'<div class="tm-rcard"><div class="tm-rtitle">Streak goal</div>'
            f'<div class="tm-rbig">{current}<small> / {goal} days</small></div>'
            f'<div class="tm-xpbar"><i style="width:{min(current / goal, 1) * 100:.0f}%"></i></div>'
            f'<div class="tm-rsub">Next badge: {goal}-day streak</div></div>'
        )
        daily_value = "{:.0f}".format(daily["wpm"]) if daily else "Open"
        daily_unit = " WPM" if daily else ""
        daily_note = "Your best today. Beat it?" if daily else "Same text for every player."
        ui.html_block(
            '<div class="tm-rcard"><div class="tm-rtitle">Today&#x27;s challenge</div>'
            f'<div class="tm-rbig">{daily_value}<small>{daily_unit}</small></div>'
            f'<div class="tm-rsub">{daily_note}</div></div>'
        )
        ui.call_stretch(st.button, "Quick start: 60s test", type="primary", key="rail_quick", on_click=_quick_start)
        ui.call_stretch(st.button, "Play daily challenge", key="rail_daily", on_click=ui.go, args=("Daily",))


def right(db: Database, player: Player) -> None:
    with st.container(key="rail_right"):
        try:
            board = db.leaderboard(limit=5)
            history = db.history(player.id)
        except DatabaseError:
            return
        rows = "".join(
            f'<div class="tm-rrow"><span>{i}. {ui.esc(r.player)}</span><b>{r.wpm:.0f}</b></div>'
            for i, r in enumerate(board.itertuples(index=False), start=1)
        ) or '<div class="tm-rsub">No scores yet. Be the first.</div>'
        ui.html_block(f'<div class="tm-rcard"><div class="tm-rtitle">Top typists</div>{rows}</div>')

        latest = None
        if not history.empty:
            earned = earned_dates(history)
            if earned:
                latest_id = max(earned, key=lambda k: (earned[k], list(BY_ID).index(k)))
                latest = (BY_ID[latest_id], earned[latest_id])
        if latest:
            ach, when = latest
            ui.html_block(
                f'<div class="tm-rcard"><div class="tm-rtitle">Latest reward</div>'
                f'<div class="tm-rname">{ui.esc(ach.name)}</div>'
                f'<div class="tm-rsub">{ach.tier.title()} badge, {when.strftime("%b %d, %Y")}</div></div>'
            )
            ui.call_stretch(st.button, "Download certificates", key="rail_rewards", on_click=ui.go, args=("Rewards",))
        else:
            ui.html_block('<div class="tm-rcard"><div class="tm-rtitle">Welcome gift</div>'
                          '<div class="tm-rsub">Finish your first test to receive a signed Certificate of Participation.</div></div>')

        tip = TIPS[date.today().toordinal() % len(TIPS)]
        ui.html_block(f'<div class="tm-rcard"><div class="tm-rtitle">Typing tip of the day</div><div class="tm-rsub" style="font-size:.92rem;color:var(--text)">{ui.esc(tip)}</div></div>')
        ui.html_block(
            f'<div class="tm-rcard founder"><div class="tm-rtitle">From the founder</div>'
            f'<div class="tm-rname">{ui.esc(config.FOUNDER_NAME)}</div><div class="tm-rsub">{config.FOUNDER_TITLE}, {config.APP_NAME}</div>'
            f'<div class="tm-rsub" style="margin-top:8px">Every badge and certificate you earn here carries my approval and signature.</div></div>'
        )
