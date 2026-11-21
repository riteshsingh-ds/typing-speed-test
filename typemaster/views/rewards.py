"""Rewards page: featured 5-day streak, downloadable certificates and badges, certificate verification."""
from __future__ import annotations

from datetime import date
from typing import Optional

import streamlit as st

from .. import config, rewards, ui
from ..database import Database, DatabaseError, Player
from ..progress import ACHIEVEMENTS, BY_ID, earned_dates, practice_days, streaks


# ------------------------------------------------------------ cached file builders
@st.cache_data(show_spinner=False, max_entries=256)
def _badge_bytes(ach_id: str, player: str, earned_iso: str) -> bytes:
    return rewards.badge_png(BY_ID[ach_id], player, date.fromisoformat(earned_iso))


@st.cache_data(show_spinner=False, max_entries=256)
def _cert_bytes(ach_id: str, player_id: int, player: str, earned_iso: str, detail: str, fmt: str) -> bytes:
    ach, earned = BY_ID[ach_id], date.fromisoformat(earned_iso)
    code = rewards.certificate_code(player_id, ach_id, earned)
    body = rewards.certificate_body(ach, detail)
    build = rewards.certificate_pdf if fmt == "pdf" else rewards.certificate_png
    return build(ach, player, earned, code, body)


def first_test_detail(history) -> str:
    """' with 21 WPM at 88.1% accuracy' for the player's very first competitive test."""
    if history.empty:
        return ""
    row = history.sort_values("created_at").iloc[0]
    return f" with {row['wpm']:.0f} WPM at {row['accuracy']:.1f}% accuracy"


def download_row(player: Player, ach_id: str, earned: date, detail: str = "", key: str = "") -> None:
    """Download buttons for one earned achievement (badge PNG, plus certificate PNG/PDF when it has one)."""
    ach, iso = BY_ID[ach_id], earned.isoformat()
    safe = player.name.replace(" ", "_")
    cols = st.columns(3 if ach.certificate else 1)
    with cols[0]:
        ui.call_stretch(st.download_button, "Badge (PNG)", _badge_bytes(ach_id, player.name, iso),
                        file_name=f"typemaster-badge-{ach_id}-{safe}.png", mime="image/png", key=f"dlb_{key}_{ach_id}")
    if ach.certificate:
        with cols[1]:
            ui.call_stretch(st.download_button, "Certificate (PNG)",
                            _cert_bytes(ach_id, player.id, player.name, iso, detail, "png"),
                            file_name=f"typemaster-certificate-{ach_id}-{safe}.png", mime="image/png",
                            key=f"dlcp_{key}_{ach_id}", type="primary")
        with cols[2]:
            ui.call_stretch(st.download_button, "Certificate (PDF)",
                            _cert_bytes(ach_id, player.id, player.name, iso, detail, "pdf"),
                            file_name=f"typemaster-certificate-{ach_id}-{safe}.pdf", mime="application/pdf",
                            key=f"dlcd_{key}_{ach_id}")


# ------------------------------------------------------------------------- page
def _verify_box(db: Database) -> None:
    with st.expander("Verify a certificate"):
        code = st.text_input("Certificate ID", placeholder="TM-0001-FIRST-261121-ABC123", key="verify_code")
        if st.button("Verify", key="verify_btn") and code.strip():
            try:
                found = rewards.verify_certificate(db, code)
            except DatabaseError as exc:
                st.error(str(exc))
                return
            if found:
                st.success(f"Genuine. {found.certificate} awarded to {found.player} on "
                           f"{found.earned.strftime('%B %d, %Y')} ({found.badge}). "
                           f"Approved by {config.FOUNDER_NAME}, {config.FOUNDER_TITLE}.")
            else:
                st.error("This certificate ID could not be verified. Check for typing mistakes.")


def render(db: Database, player: Player) -> None:
    ui.page_header("Rewards", "Badges and certificates you have earned, each approved and signed by the founder.")
    try:
        history = db.history(player.id)
    except DatabaseError as exc:
        ui.error_state("Your rewards could not be loaded", str(exc))
        return

    if history.empty:
        ui.empty_state("Your first certificate is waiting",
                       "Finish any test and you receive a Certificate of Participation you can download, print and share.")
        ui.call_stretch(st.button, "Take my first test", type="primary", key="rw_go", on_click=ui.go, args=("Practice",))
        _verify_box(db)
        return

    earned = earned_dates(history)
    current, best = streaks(practice_days(history))
    detail = first_test_detail(history)

    # ---- featured streak challenge
    goal = config.STREAK_GOAL
    done = "streak5" in earned
    got = goal if done else min(current, goal)
    if done:
        status = "Unlocked on " + earned["streak5"].strftime("%B %d, %Y")
    else:
        status = "{} of {} days. Practice today to keep going.".format(got, goal)
    days_html = "".join('<span class="tm-day {}">{}</span>'.format("on" if i < got else "", i + 1) for i in range(goal))
    ui.html_block(
        '<div class="tm-feature-card"><div><div class="tm-eyebrow">Featured challenge</div>'
        '<h3>{goal}-day streak</h3><p>Practice {goal} days in a row to unlock the {goal}-day streak badge and the '
        'Certificate of Consistency, approved and signed by {founder}.</p></div>'
        '<div><div class="tm-days">{days}</div>'
        '<div class="tm-sub" style="color:var(--muted);margin-top:8px">{status}</div></div></div>'.format(
            goal=goal, founder=ui.esc(config.FOUNDER_NAME), days=days_html, status=ui.esc(status))
    )
    if done:
        download_row(player, "streak5", earned["streak5"], key="feat")
    else:
        ui.call_stretch(st.button, "Practice now", type="primary", key="rw_practice", on_click=ui.go, args=("Practice",))

    # ---- certificates
    ui.section_title("Certificates", "Printable, signed and verifiable")
    cert_ids = [a.id for a in ACHIEVEMENTS if a.certificate]
    for row_start in range(0, len(cert_ids), 2):
        cols = st.columns(2)
        for col, ach_id in zip(cols, cert_ids[row_start:row_start + 2]):
            ach = BY_ID[ach_id]
            with col:
                got_it = ach_id in earned
                code = rewards.certificate_code(player.id, ach_id, earned[ach_id]) if got_it else ""
                sub = f"Earned {earned[ach_id].strftime('%b %d, %Y')}  |  {code}" if got_it else f"Locked: {ach.description}"
                ui.html_block(
                    f'<div class="tm-cert {"on" if got_it else "off"}"><span class="state">{"UNLOCKED" if got_it else "LOCKED"}</span>'
                    f'<b>{ui.esc(ach.certificate)}</b><span class="what">{ui.esc(ach.name)}</span>'
                    f'<span class="code">{ui.esc(sub)}</span></div>')
                if got_it:
                    download_row(player, ach_id, earned[ach_id], detail if ach_id == "first" else "", key="cert")

    # ---- badges
    ui.section_title("Badges", f"{len(earned)} of {len(ACHIEVEMENTS)} unlocked")
    for row_start in range(0, len(ACHIEVEMENTS), 3):
        cols = st.columns(3)
        for col, ach in zip(cols, ACHIEVEMENTS[row_start:row_start + 3]):
            with col:
                got_it = ach.id in earned
                when = f"Earned {earned[ach.id].strftime('%b %d, %Y')}" if got_it else ach.description
                ui.html_block(
                    f'<div class="tm-ach {"on" if got_it else "off"} tier-{ach.tier}"><span class="state">{ui.esc(ach.tier.upper()) if got_it else "LOCKED"}</span>'
                    f'<b>{ui.esc(ach.name)}</b><span>{ui.esc(when)}</span></div>')
                if got_it:
                    ui.call_stretch(st.download_button, "Download badge", _badge_bytes(ach.id, player.name, earned[ach.id].isoformat()),
                                    file_name=f"typemaster-badge-{ach.id}.png", mime="image/png", key=f"dl_badge_{ach.id}")
    _verify_box(db)
