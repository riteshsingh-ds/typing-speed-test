from datetime import date, timedelta

import pandas as pd
import pytest

from typemaster import config
from typemaster.drills import build_drill
from typemaster.metrics import char_stats
from typemaster.passages import daily_challenge
from typemaster.progress import (ACHIEVEMENTS, KeyStat, level_info, streaks, unlocked_ids, weak_keys, xp_for_result)


def hist(rows):
    base = dict(wpm=30.0, accuracy=95.0, difficulty="Easy", duration_sec=60, mode="standard",
                correct_chars=150, typed_chars=160, incorrect_chars=10,
                created_at=pd.Timestamp("2026-11-01", tz="UTC"))
    return pd.DataFrame([{**base, **r} for r in rows])


def test_xp_rewards_accuracy():
    clean, sloppy = xp_for_result(300, 100), xp_for_result(300, 80)
    assert clean == 75 and sloppy == 48 and clean > sloppy
    assert xp_for_result(0, 0) == 0


@pytest.mark.parametrize("xp,level", [(0, 1), (99, 1), (100, 2), (399, 2), (400, 3), (1600, 5)])
def test_levels(xp, level):
    assert level_info(xp).level == level


def test_level_progress_and_titles():
    info = level_info(250)
    assert info.level == 2 and info.floor == 100 and info.ceiling == 400 and info.progress == pytest.approx(0.5)
    assert level_info(10 ** 7).title == "Legend"


def test_streaks():
    t = date(2026, 11, 20)
    d = lambda n: t - timedelta(days=n)  # noqa: E731
    assert streaks([], t) == (0, 0)
    assert streaks([d(0), d(1), d(2)], t) == (3, 3)
    assert streaks([d(1), d(2)], t) == (2, 2)            # today still pending
    assert streaks([d(2), d(3)], t) == (0, 2)            # streak broken
    assert streaks([d(0), d(1), d(5), d(6), d(7), d(8)], t) == (2, 4)
    assert streaks([d(0), d(0), d(0)], t) == (1, 1)


def test_achievements_unlock_correctly():
    assert unlocked_ids(hist([])) == set()
    ids = unlocked_ids(hist([dict(wpm=65, accuracy=99, typed_chars=300)]))
    assert {"first", "wpm40", "wpm60", "sharp"} <= ids and "wpm80" not in ids and "flawless" not in ids
    drill_only = unlocked_ids(hist([dict(wpm=120, mode="drill")]))
    assert "wpm100" not in drill_only and "drill" in drill_only      # drills never count for speed badges
    assert "daily" in unlocked_ids(hist([dict(mode="daily")]))
    assert "hard" in unlocked_ids(hist([dict(difficulty="Hard", wpm=55)]))
    assert "endurance" in unlocked_ids(hist([dict(duration_sec=120, wpm=41)]))
    assert len({a.id for a in ACHIEVEMENTS}) == len(ACHIEVEMENTS) >= 15


def test_char_stats_counts_corrected_mistakes():
    s = char_stats("Hello a", "Hexlo a", ever_wrong=[1])
    assert s["l"] == [2, 1] and s["e"] == [1, 1] and s["space"] == [1, 0] and s["h"] == [1, 0]
    assert char_stats("ab", "ab", [0])["a"] == [1, 1]     # fixed mistake still counts


def test_weak_keys_need_enough_attempts():
    agg = {"q": [config.MIN_KEY_ATTEMPTS, 5], "z": [3, 3], "a": [100, 0], "x": [20, 4]}
    assert [k.key for k in weak_keys(agg)] == ["q", "x"]   # z too few attempts, a has no errors
    assert weak_keys({}) == []


def test_drill_focuses_on_weak_keys_and_is_long_enough():
    weak = [KeyStat("q", 20, 10), KeyStat("z", 20, 8)]
    for duration in (30, 60):
        text = build_drill(weak, duration)
        assert len(text) >= config.TARGET_CHARS[duration]
        assert "  " not in text and text.isascii()
        share = sum(1 for t in text.split() if "q" in t or "z" in t) / len(text.split())
        assert share > 0.5
    with pytest.raises(ValueError):
        build_drill(weak, 45)
    assert len(build_drill([], 30)) >= 450               # no weak keys: still returns a valid drill


def test_daily_challenge_is_deterministic_per_day():
    a, b = daily_challenge(date(2026, 11, 20)), daily_challenge(date(2026, 11, 20))
    assert a.text == b.text and len(a.text) >= config.TARGET_CHARS[config.DAILY_DURATION]
    others = {daily_challenge(date(2026, 11, 20) + timedelta(days=i)).text for i in range(1, 8)}
    assert len(others | {a.text}) > 4
