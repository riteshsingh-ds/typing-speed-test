import io
from datetime import date, timedelta

import pandas as pd
import pytest
from PIL import Image

from typemaster import config, rewards
from typemaster.database import Database
from typemaster.metrics import compute_metrics
from typemaster.progress import ACHIEVEMENTS, BY_ID, earned_dates, next_streak_goal
from typemaster.utils import to_local


def png_size(data: bytes):
    img = Image.open(io.BytesIO(data))
    assert img.format == "PNG"
    return img.size


@pytest.mark.parametrize("ach", ACHIEVEMENTS, ids=lambda a: a.id)
def test_every_badge_renders(ach):
    assert png_size(rewards.badge_png(ach, "Ritesh Kumar Singh", date(2026, 11, 21))) == (1080, 1350)


def test_certificates_render_png_and_pdf():
    ach = BY_ID["first"]
    code = rewards.certificate_code(1, "first", date(2026, 11, 21))
    body = rewards.certificate_body(ach, " with 21 WPM at 88.1% accuracy")
    assert "21 WPM" in body
    assert png_size(rewards.certificate_png(ach, "Ritesh Kumar Singh", date(2026, 11, 21), code, body)) == (1754, 1240)
    pdf = rewards.certificate_pdf(ach, "A" * 60, date(2026, 11, 21), code, body)   # very long name still fits
    assert pdf.startswith(b"%PDF")


def test_only_designated_achievements_have_certificates():
    titles = {a.id: a.certificate for a in ACHIEVEMENTS if a.certificate}
    assert {"first", "streak5", "wpm40", "wpm60", "wpm80", "wpm100", "sharp"} == set(titles)
    assert titles["streak5"] == "Certificate of Consistency" and titles["first"] == "Certificate of Participation"


def test_branding_and_approval_present_in_config():
    assert config.FOUNDER_NAME == "Ritesh Kumar Singh" and config.FOUNDER_TITLE == "Founder & CEO"


def history_for_days(wpms):
    """One test per consecutive day, oldest first."""
    start = pd.Timestamp("2026-11-01 12:00", tz="UTC")
    rows = [dict(wpm=w, accuracy=97.0, difficulty="Easy", duration_sec=60, mode="standard", correct_chars=200,
                 typed_chars=210, incorrect_chars=10, created_at=start + pd.Timedelta(days=i)) for i, w in enumerate(wpms)]
    return pd.DataFrame(rows)


def test_earned_dates_find_the_day_each_badge_was_unlocked():
    h = history_for_days([20, 30, 45, 50, 65, 70])
    days = list(to_local(h["created_at"]).dt.date)
    e = earned_dates(h)
    assert e["first"] == days[0]
    assert e["wpm40"] == days[2] and e["wpm60"] == days[4]
    assert e["streak3"] == days[2] and e["streak5"] == days[4]
    assert "streak7" not in e and "wpm80" not in e


def test_streak_with_gap_does_not_unlock_five_day_badge():
    h = history_for_days([30, 30, 30, 30, 30])
    h = h.drop(index=2).reset_index(drop=True)          # missing day breaks the run
    assert "streak5" not in earned_dates(h)


def test_earned_dates_empty():
    assert earned_dates(history_for_days([]).iloc[0:0]) == {}


def test_next_streak_goal():
    assert [next_streak_goal(n) for n in (0, 2, 3, 4, 5, 6, 7, 29, 40)] == [3, 3, 5, 5, 7, 7, 30, 30, 30]


@pytest.fixture()
def db_with_player(tmp_path):
    db = Database(tmp_path / "r.db")
    player = db.get_or_create_player("Ana")
    m = compute_metrics("a" * 300, "a" * 300, 60)
    db.save_result(player.id, "t1", 60, "Easy", m, [])
    first_day = earned_dates(db.history(player.id))["first"]
    return db, player, first_day


def test_certificate_codes_verify(db_with_player):
    db, player, day = db_with_player
    code = rewards.certificate_code(player.id, "first", day)
    assert code.startswith(f"TM-{player.id:04d}-FIRST-")
    v = rewards.verify_certificate(db, code)
    assert v and v.player == "Ana" and v.certificate == "Certificate of Participation" and v.earned == day
    assert rewards.verify_certificate(db, code.lower()) is not None        # case-insensitive
    assert rewards.verify_certificate(db, f"  {code}  ") is not None       # surrounding spaces ok


def test_forged_or_wrong_certificates_fail(db_with_player):
    db, player, day = db_with_player
    good = rewards.certificate_code(player.id, "first", day)
    tampered = good[:-1] + ("0" if good[-1] != "0" else "1")
    other_day = rewards.certificate_code(player.id, "first", day + timedelta(days=1))
    unearned = rewards.certificate_code(player.id, "streak5", day)          # validly signed but never earned
    nobody = rewards.certificate_code(999, "first", day)
    not_cert = rewards.certificate_code(player.id, "ten", day)              # badge without a certificate
    for bad in [tampered, other_day, unearned, nobody, not_cert, "", "garbage", "TM-0001-FIRST-999999-ABCDEF", None]:
        assert rewards.verify_certificate(db, bad) is None, bad


def test_secret_changes_signature(monkeypatch):
    a = rewards.certificate_code(1, "first", date(2026, 1, 1))
    monkeypatch.setattr(config, "CERT_SECRET", "another-secret")
    assert rewards.certificate_code(1, "first", date(2026, 1, 1)) != a
