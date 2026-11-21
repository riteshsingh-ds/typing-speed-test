"""The live typing arena and result screen, shared by Practice, Daily and Key Doctor."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

import streamlit as st

from .. import analytics, config, ui
from ..cards import result_card_svg
from ..database import Database, DatabaseError, Player
from ..metrics import speed_tier
from ..passages import build_challenge
from ..services import TestResult, process_submission, retry_save
from ..progress import BY_ID
from ..typing_widget import typing_engine
from . import rewards as rewards_view

MODE_LABEL = {"standard": "Practice", "daily": "Daily Challenge", "drill": "Key Doctor drill"}


def active() -> bool:
    return st.session_state.phase in ("running", "finished") and st.session_state.test is not None


# ------------------------------------------------------------------ actions
def launch(difficulty: str, duration: int, text: Optional[str] = None, mode: str = "standard",
           challenge_date: Optional[str] = None) -> None:
    """Start a test. ``text=None`` draws a fresh passage; otherwise the given text is used."""
    ss = st.session_state
    if text is None:
        last = ss.last_first
        avoid = last[1] if last and last[0] == difficulty else None
        challenge = build_challenge(difficulty, duration, avoid_first=avoid)
        text, ss.last_first = challenge.text, (difficulty, challenge.first_index)
    ss.test = {"id": uuid.uuid4().hex, "text": text, "duration": duration, "difficulty": difficulty,
               "mode": mode, "challenge_date": challenge_date}
    ss.test_page = ss.get("nav")
    ss.result = None
    ss.phase = "running"


def _restart() -> None:
    t = st.session_state.test
    launch(t["difficulty"], t["duration"], t["text"], t["mode"], t["challenge_date"])


def _new_passage() -> None:
    t = st.session_state.test
    launch(t["difficulty"], t["duration"])


def back_to_setup() -> None:
    ss = st.session_state
    ss.phase, ss.test, ss.result = "idle", None, None


def _retry(db: Database, player: Player) -> None:
    st.session_state.result = retry_save(db, player.id, st.session_state.result)


# ------------------------------------------------------------------- render
def render(db: Database, player: Player) -> None:
    if st.session_state.phase == "running":
        _running(db, player)
    else:
        _finished(db, player)


def _running(db: Database, player: Player) -> None:
    ss = st.session_state
    test = ss.test
    if "pb" not in test:  # looked up once so the component arguments never change mid-test
        try:
            best = db.personal_best(player.id)
            test["pb"] = best["wpm"] if best else None
        except DatabaseError:
            test["pb"] = None

    chips = ui.badge(MODE_LABEL[test["mode"]], "amber") + ui.badge(f"{test['duration']} seconds")
    if test["mode"] != "drill":
        chips += ui.badge(test["difficulty"])
    ui.html_block(f'<div class="tm-chips">{chips}</div>')

    payload = typing_engine(text=test["text"], duration=test["duration"], test_id=test["id"],
                            personal_best=test["pb"], key=f"engine-{test['id']}")

    cols = st.columns(3 if test["mode"] == "standard" else 2)
    with cols[0]:
        ui.call_stretch(st.button, "Restart", key="restart_btn", on_click=_restart)
    if test["mode"] == "standard":
        with cols[1]:
            ui.call_stretch(st.button, "New passage", key="new_btn", on_click=_new_passage)
    with cols[-1]:
        ui.call_stretch(st.button, "Cancel", key="cancel_btn", on_click=back_to_setup)

    # The engine returns a value exactly once, when the test ends.
    if isinstance(payload, dict) and payload.get("test_id") == test["id"] and test["id"] not in ss.submitted:
        ss.submitted.add(test["id"])  # mark first: a rerun can never submit the same test twice
        with st.spinner("Scoring your result..."):
            ss.result = process_submission(db, player.id, test, payload)
        ss.phase = "finished"
        st.rerun()


def _actions(result: Optional[TestResult] = None) -> None:
    mode = st.session_state.test["mode"]
    cols = st.columns(3 if mode == "standard" else 2)
    with cols[0]:
        ui.call_stretch(st.button, "Try again", key="again_btn", type="primary", on_click=_restart)
    if mode == "standard":
        with cols[1]:
            ui.call_stretch(st.button, "New passage", key="next_btn", on_click=_new_passage)
    with cols[-1]:
        ui.call_stretch(st.button, "Done", key="settings_btn", on_click=back_to_setup)


def _setup_label(result: TestResult) -> str:
    if result.mode == "daily":
        return f"Daily Challenge, {result.challenge_date}"
    if result.mode == "drill":
        return f"Key Doctor drill, {result.duration} seconds"
    return f"{result.duration} seconds, {result.difficulty}"


def _finished(db: Database, player: Player) -> None:
    result: TestResult = st.session_state.result
    if result.error or result.metrics is None:
        ui.error_state("This test was not scored", result.error or "Something went wrong.")
        _actions()
        return

    m = result.metrics
    notes = {
        "first": ("First score saved", "good", "That is your baseline. Every test from here is a chance to beat it."),
        "overall": ("New personal best", "good", "Your fastest result so far."),
        "category": ("Best for this setup", "amber", f"Your fastest on {result.duration} seconds, {result.difficulty}."),
    }
    badge_html, note = "", f"{m.typed_chars} characters typed in {m.elapsed_sec:.1f} seconds."
    if result.pb_status in notes:
        label, tone, note = notes[result.pb_status]
        badge_html = ui.badge(label, tone)
    if result.mode == "drill":
        note = "Drills train your weak keys and never affect your records or the leaderboards."

    ui.html_block(
        f'<div class="tm-result"><div><div class="tm-bigwpm">{m.wpm:.0f}<small>WPM</small></div>'
        f'<div class="tm-tier">{ui.esc(speed_tier(m.wpm))}</div></div>'
        f'<div class="tm-result-note">{badge_html}<div style="margin-top:8px">{ui.esc(note)}</div></div></div>'
    )

    gains = []
    if result.saved:
        gains.append(ui.badge(f"+{result.xp_gain} XP", "amber"))
    if result.level_up:
        gains.append(ui.badge(f"Level up! You are now level {result.level_up}", "good"))
    gains += [ui.badge(f"Badge unlocked: {name}", "good") for name in result.new_badges]
    if result.mode == "daily" and result.saved:
        try:
            board = db.daily_leaderboard(result.challenge_date)
            names = [n.lower() for n in board["player"]]
            if player.name.lower() in names:
                gains.append(ui.badge(f"Today's rank: #{names.index(player.name.lower()) + 1} of {len(names)}", "amber"))
        except DatabaseError:
            pass
    if gains:
        ui.html_block(f'<div class="tm-gain">{"".join(gains)}</div>')

    earned_certs = [i for i in result.new_badge_ids if BY_ID[i].certificate]
    for cert_id in earned_certs:
        ach = BY_ID[cert_id]
        ui.html_block(
            f'<div class="tm-cert on"><span class="state">NEW</span><b>{ui.esc(ach.certificate)} unlocked</b>'
            f'<span class="what">Approved and signed by {ui.esc(config.FOUNDER_NAME)}, {ui.esc(config.FOUNDER_TITLE)}</span></div>')
        detail = f" with {m.wpm:.0f} WPM at {m.accuracy:.1f}% accuracy" if cert_id == "first" else ""
        rewards_view.download_row(player, cert_id, date.today(), detail, key="res")

    if result.save_error:
        st.warning(f"Your result could not be saved to history. {result.save_error}")
        ui.call_stretch(st.button, "Retry saving", key="retry_save_btn", on_click=_retry, args=(db, player))
    elif result.duplicate:
        st.info("This result was already saved, so it was not added twice.")

    ui.card_grid([
        ui.card("Accuracy", f"{m.accuracy:.1f}%", "", "mint"),
        ui.card("Raw speed", f"{m.raw_wpm:.0f}", "WPM before mistakes"),
        ui.card("Time", f"{m.elapsed_sec:.0f}s", f"{result.duration}-second test"),
        ui.card("Correct characters", str(m.correct_chars), "", "mint"),
        ui.card("Mistakes", str(m.incorrect_chars), "", "coral" if m.incorrect_chars else ""),
        ui.card("Characters typed", str(m.typed_chars)),
    ], cols=3)

    if len(result.series) >= 2:
        best = None
        try:
            pb = db.personal_best(player.id)
            best = pb["wpm"] if pb else None
        except DatabaseError:
            pass
        ui.show_chart(analytics.pace_chart(result.series, best, result.ghost))

    svg = result_card_svg(player.name, m.wpm, m.accuracy, speed_tier(m.wpm), _setup_label(result), date.today().strftime("%b %d, %Y"))
    _actions()
    st.download_button("Download result card (SVG)", svg.encode("utf-8"), file_name=f"typemaster-{m.wpm:.0f}wpm.svg",
                       mime="image/svg+xml", key="card_dl")
