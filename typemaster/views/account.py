"""Sign-in, onboarding (create account / claim an old profile) and the account menu."""
from __future__ import annotations

import os

import streamlit as st

from .. import auth, config, ui
from ..database import Database, DatabaseError, Player
from ..state import reset_test, set_player
from ..validators import ValidationError, validate_player_name

ALLOW_CLAIM = os.environ.get("TYPEMASTER_ALLOW_CLAIM", "1").lower() not in {"0", "off", "false"}


def _hero(title_html: str, body: str, side: str) -> None:
    ui.html_block(
        f'<div class="tm-hero"><div class="tm-hero-main"><div class="tm-brand"><div class="tm-logo">TM</div>'
        f'<div class="tm-title">{config.APP_NAME}</div></div>'
        f'<h1>{title_html}</h1><p>{ui.esc(body)}</p></div>'
        f'<div class="tm-hero-side"><h4>Why sign in?</h4>{side}</div></div>'
    )


def _footer() -> None:
    ui.html_block(f'<div class="tm-footer"><div><b>{config.APP_NAME}</b></div>'
                  f'<div>{config.FOUNDER_TITLE}: <b>{ui.esc(config.FOUNDER_NAME)}</b></div></div>')


def login_screen() -> None:
    """Shown to visitors who are not signed in (Google login configured)."""
    side = "".join(f'<div class="tm-mini"><span>{ui.esc(t)}</span></div>' for t in (
        "Your scores, streaks and certificates follow you to any device.",
        "One account per person. No one can use your name or your certificates.",
        "Your email stays private. Only your display name is shown.",
    ))
    _hero("Your keyboard, <em>mastered.</em>",
          "Daily challenges, a weak-key doctor, ghost races, streaks and signed certificates. Sign in with Google to begin.",
          side)
    ui.call_stretch(st.button, "Continue with Google", type="primary", key="login_btn", on_click=auth.login)
    _footer()


def local_notice() -> None:
    st.caption("Local mode: Google login is not configured, so names are not protected. "
               "See the README to switch on real accounts.")


def onboarding(db: Database, user: auth.AuthUser) -> None:
    """First login with this email: create a new account or claim an old name-only profile."""
    ui.page_header(f"Welcome, {user.name}", f"Signed in as {user.email}. Let us set up your TypeMaster account.")
    st.subheader("New to TypeMaster?")
    with st.form("create_account"):
        name = st.text_input("Display name (other players can share it)", value=user.name[: config.NAME_MAX], max_chars=config.NAME_MAX)
        create = st.form_submit_button("Create my account", type="primary")
    if create:
        try:
            player = db.create_account(validate_player_name(name), user.email)
        except (ValidationError, DatabaseError) as exc:
            st.error(str(exc))
        else:
            set_player(player)
            st.rerun()

    if not ALLOW_CLAIM:
        return
    st.subheader("Played before without an account?")
    st.caption("Enter the name you used before. If that profile is still unclaimed you can attach it to this Google account "
               "and keep your scores, badges and certificates.")
    with st.form("claim_lookup"):
        old = st.text_input("Your old player name", max_chars=config.NAME_MAX)
        look = st.form_submit_button("Find my old profile")
    if look:
        try:
            st.session_state["claim_matches"] = db.find_unclaimed(old) if old.strip() else []
            st.session_state["claim_searched"] = old.strip()
        except DatabaseError as exc:
            st.error(str(exc))
    matches = st.session_state.get("claim_matches")
    if matches is None:
        return
    if not matches:
        st.info(f"No unclaimed profile named \"{st.session_state.get('claim_searched', '')}\" was found.")
        return
    for m in matches:
        st.write(f"**{m['name']}**: {m['tests']} tests, best {m['best_wpm']:.0f} WPM")
        if st.button("This is my profile. Claim it.", key=f"claim_{m['id']}"):
            try:
                ok = db.claim_player(m["id"], user.email)
            except DatabaseError as exc:
                st.error(str(exc))
                return
            if ok:
                st.session_state.pop("claim_matches", None)
                set_player(db.get_player(m["id"]))
                st.rerun()
            st.error("That profile was just claimed by someone else.")


# ------------------------------------------------------------------ account menu
def _sign_out() -> None:
    st.session_state.player = None
    reset_test()
    auth.logout()


def menu(db: Database, player: Player, auth_on: bool, sign_in_local) -> None:
    """Popover next to the logo: rename / sign out / delete (login mode) or switch player (local mode)."""
    with ui.call_stretch(st.popover, player.name):
        if not auth_on:
            with st.form("switch_player"):
                new_name = st.text_input("Player name", value=player.name, max_chars=config.NAME_MAX)
                switch = st.form_submit_button("Switch player")
            if switch:
                error = sign_in_local(db, new_name)
                if error:
                    st.error(error)
                else:
                    st.rerun()
            return

        st.caption(player.email or "")
        with st.form("rename_form"):
            new_name = st.text_input("Display name", value=player.name, max_chars=config.NAME_MAX)
            save = st.form_submit_button("Save name")
        if save:
            try:
                clean = validate_player_name(new_name)
                db.rename_player(player.id, clean)
                set_player(Player(player.id, clean, player.email))
            except (ValidationError, DatabaseError) as exc:
                st.error(str(exc))
            else:
                st.rerun()
        ui.call_stretch(st.button, "Sign out", key="signout_btn", on_click=_sign_out)
        with st.expander("Delete my account"):
            st.write("Permanently deletes your account, scores, badges and certificates. This cannot be undone.")
            sure = st.checkbox("I understand", key="delete_account_confirm")
            if st.button("Delete everything", disabled=not sure, key="delete_account_btn"):
                try:
                    db.delete_player(player.id)
                except DatabaseError as exc:
                    st.error(str(exc))
                else:
                    _sign_out()
