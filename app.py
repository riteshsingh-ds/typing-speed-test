"""TypeMaster - Typing Speed Challenge.  Run with:  streamlit run app.py"""
from __future__ import annotations

import streamlit as st

from typemaster import auth, config, splash, ui
from typemaster.database import Database, DatabaseError
from typemaster.state import get_player, init_state, reset_test, set_player
from typemaster.styles import inject_css
from typemaster.validators import ValidationError, validate_player_name
from typemaster.views import account, dashboard, daily, home, keydoctor, leaderboard, practice, profile, rails, rewards

try:
    from PIL import Image
    _ICON = Image.open(config.PROJECT_ROOT / "assets" / "favicon.png")
except Exception:  # Pillow or the file is missing: fall back to a plain text icon
    _ICON = "T"

st.set_page_config(
    page_title="TypeMaster - Typing Speed Challenge",
    page_icon=_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

PAGES = {
    "Home": home.render, "Practice": practice.render, "Daily": daily.render,
    "Key Doctor": keydoctor.render, "Progress": profile.render, "Rewards": rewards.render,
    "Analytics": dashboard.render, "Leaderboard": leaderboard.render,
}


@st.cache_resource(show_spinner=False)
def get_database() -> Database:
    return Database(config.DB_PATH)


def _sign_in(db: Database, raw_name: str) -> str | None:
    """Validate the name and sign in. Returns an error message on failure."""
    try:
        player = db.get_or_create_player(validate_player_name(raw_name))
    except (ValidationError, DatabaseError) as exc:
        return str(exc)
    set_player(player)
    st.query_params["player"] = player.name  # survives a browser refresh
    return None


def _brand() -> None:
    ui.html_block(
        f'<div class="tm-brand"><div class="tm-logo">TM</div><div>'
        f'<div class="tm-title">{config.APP_NAME}</div>'
        f'<div class="tm-tagline">{config.APP_TAGLINE}</div></div></div>'
    )


def _welcome(db: Database) -> None:
    """Local mode only (no Google login configured): choose a player name."""
    ui.html_block(
        f'<div class="tm-hero"><div class="tm-hero-main"><div class="tm-brand"><div class="tm-logo">TM</div>'
        f'<div class="tm-title">{config.APP_NAME}</div></div>'
        f'<h1>Your keyboard, <em>mastered.</em></h1>'
        f'<p>Daily challenges, a weak-key doctor, ghost races against your best run, XP and streaks.</p>'
        f'<div class="tm-demo"><span class="ok">Practice makes permanent, so practice </span>'
        f'<span class="bad">c</span><span class="ok">arefully</span><span class="caret"></span></div></div>'
        f'<div class="tm-hero-side"><h4>Who is typing?</h4>'
        f'<div class="tm-mini"><span>Your name keeps your scores, streaks and badges.</span></div></div></div>'
    )
    account.local_notice()
    with st.form("welcome_form"):
        name = st.text_input("Player name", max_chars=config.NAME_MAX, placeholder="e.g. Ritesh")
        submitted = st.form_submit_button("Enter TypeMaster", type="primary")
    if submitted:
        error = _sign_in(db, name)
        if error:
            st.error(error)
        else:
            st.rerun()
    ui.html_block(f'<div class="tm-footer"><div><b>{config.APP_NAME}</b></div>'
                  f'<div>{config.FOUNDER_TITLE}: <b>{ui.esc(config.FOUNDER_NAME)}</b></div></div>')


def _resolve_player(db: Database, auth_on: bool):
    """Return the signed-in Player, or render the right sign-in screen and return None."""
    if not auth_on:                                   # local / development mode
        player = get_player()
        if player is None and st.query_params.get("player"):
            if _sign_in(db, st.query_params["player"]) is None:
                player = get_player()
        if player is None:
            _welcome(db)
        return player

    user = auth.current_user()
    if user is None:
        account.login_screen()
        return None
    if not user.verified:
        _brand()
        ui.error_state("Your Google email is not verified", "Verify your email with Google, then sign in again.")
        return None
    player = get_player()
    if player is None or (player.email or "") != user.email:
        player = db.get_player_by_email(user.email)
        if player is None:
            st.session_state.player = None          # never keep a previous account's data around
            account.onboarding(db, user)
            return None
        set_player(player)
    return player


def main() -> None:
    inject_css()
    init_state()

    if not st.session_state.booted:
        db = splash.show(get_database)
        st.session_state.booted = True
    else:
        try:
            db = get_database()
        except DatabaseError:
            db = None
    if db is None:
        _brand()
        ui.error_state("The database could not be opened",
                       f"Check that the folder {config.DB_PATH.parent} exists and is writable, then reload.")
        st.stop()

    auth_on = auth.is_configured()
    player = _resolve_player(db, auth_on)
    if player is None:
        return

    brand_col, player_col = st.columns([4, 1.3], vertical_alignment="center")
    with brand_col:
        _brand()
    with player_col:
        account.menu(db, player, auth_on, _sign_in)

    page = st.radio("Navigate", list(PAGES), horizontal=True, key="nav", label_visibility="collapsed")
    ss = st.session_state
    if ss.phase != "idle" and ss.test_page != page:   # leaving the page cancels an unfinished test
        reset_test()

    if ss.phase == "running":                      # focus mode: no side panels while the clock is ticking
        _, centre, _ = st.columns([0.5, 3, 0.5])
        with centre:
            PAGES[page](db, player)
    else:
        left_rail, centre, right_rail = st.columns([1.0, 3.1, 1.05], gap="large")
        with left_rail:
            rails.left(db, player)
        with centre:
            PAGES[page](db, player)
        with right_rail:
            rails.right(db, player)


main()
