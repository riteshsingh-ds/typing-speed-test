"""XP, levels, streaks and achievements - all derived from saved results (pure, testable)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Iterable

import pandas as pd

from . import config
from .utils import to_local

LEVEL_TITLES = ("Rookie", "Typist", "Speedster", "Keysmith", "Virtuoso", "Grandmaster", "Legend")


# --------------------------------------------------------------------------- XP
def xp_for_result(correct_chars: int, accuracy: float) -> int:
    """Accuracy is squared so sloppy speed earns far less than clean typing."""
    return int(round(correct_chars * (accuracy / 100.0) ** 2 / 4))


def total_xp(history: pd.DataFrame) -> int:
    if history.empty:
        return 0
    return int(sum(xp_for_result(c, a) for c, a in zip(history["correct_chars"], history["accuracy"])))


@dataclass(frozen=True)
class LevelInfo:
    level: int
    title: str
    xp: int
    floor: int       # XP where this level starts
    ceiling: int     # XP where the next level starts
    progress: float  # 0..1 inside the level


def level_info(xp: int) -> LevelInfo:
    xp = max(0, int(xp))
    level = int(math.sqrt(xp / 100)) + 1
    floor, ceiling = 100 * (level - 1) ** 2, 100 * level ** 2
    return LevelInfo(level, LEVEL_TITLES[min(level - 1, len(LEVEL_TITLES) - 1)], xp, floor, ceiling,
                     (xp - floor) / (ceiling - floor))


# ----------------------------------------------------------------------- streaks
def practice_days(history: pd.DataFrame) -> list[date]:
    if history.empty:
        return []
    return sorted(set(to_local(history["created_at"]).dt.date))


def streaks(days: Iterable[date], today: date | None = None) -> tuple[int, int]:
    """Return ``(current, best)`` consecutive-day streaks. Today may still be pending."""
    today = today or date.today()
    ordered = sorted(set(days))
    if not ordered:
        return 0, 0
    best = run = 1
    for prev, cur in zip(ordered, ordered[1:]):
        run = run + 1 if cur - prev == timedelta(days=1) else 1
        best = max(best, run)
    current = 0
    if ordered[-1] >= today - timedelta(days=1):
        current, cursor = 1, ordered[-1]
        for d in reversed(ordered[:-1]):
            if cursor - d == timedelta(days=1):
                current, cursor = current + 1, d
            else:
                break
    return current, best


# ------------------------------------------------------------------ achievements
@dataclass(frozen=True)
class Achievement:
    id: str
    name: str
    description: str
    check: Callable[[pd.DataFrame, int], bool]   # (history, best_streak) -> unlocked?
    tier: str = "bronze"                         # bronze | silver | gold | platinum
    icon: str = "star"                           # star | target | crown | diamond | check
    certificate: str | None = None               # certificate title when this badge also earns one


def _best(h: pd.DataFrame, col: str = "wpm", **where) -> float:
    h = h[h["mode"] != "drill"]
    for key, value in where.items():
        h = h[h[key] == value]
    return float(h[col].max()) if not h.empty else 0.0


def _clean(h: pd.DataFrame, accuracy: float) -> bool:
    h = h[(h["typed_chars"] >= 150) & (h["accuracy"] >= accuracy)]
    return not h.empty


ACHIEVEMENTS: tuple[Achievement, ...] = (
    Achievement("first", "First keystrokes", "Finish your first test", lambda h, s: len(h) >= 1,
                "bronze", "star", "Certificate of Participation"),
    Achievement("ten", "Regular", "Finish 10 tests", lambda h, s: len(h) >= 10, "bronze", "check"),
    Achievement("fifty", "Marathoner", "Finish 50 tests", lambda h, s: len(h) >= 50, "silver", "check"),
    Achievement("hundred", "Centurion", "Finish 100 tests", lambda h, s: len(h) >= 100, "gold", "crown"),
    Achievement("wpm40", "Steady hands", "Reach 40 WPM", lambda h, s: _best(h) >= 40,
                "bronze", "star", "Certificate of Speed"),
    Achievement("wpm60", "Fast fingers", "Reach 60 WPM", lambda h, s: _best(h) >= 60,
                "silver", "star", "Certificate of Speed"),
    Achievement("wpm80", "Blazing", "Reach 80 WPM", lambda h, s: _best(h) >= 80,
                "gold", "star", "Certificate of Speed"),
    Achievement("wpm100", "Elite", "Reach 100 WPM", lambda h, s: _best(h) >= 100,
                "platinum", "crown", "Certificate of Speed"),
    Achievement("sharp", "Sharpshooter", "98% accuracy on 150+ characters", lambda h, s: _clean(h, 98),
                "silver", "target", "Certificate of Accuracy"),
    Achievement("flawless", "Flawless", "100% accuracy on 150+ characters", lambda h, s: _clean(h, 100),
                "gold", "target"),
    Achievement("hard", "Hard mode", "Reach 50 WPM on Hard", lambda h, s: _best(h, difficulty="Hard") >= 50,
                "silver", "diamond"),
    Achievement("endurance", "Endurance", "Reach 40 WPM in a 120-second test",
                lambda h, s: _best(h, duration_sec=120) >= 40, "silver", "diamond"),
    Achievement("streak3", "On a roll", "Practice 3 days in a row", lambda h, s: s >= 3, "bronze", "diamond"),
    Achievement("streak5", "Five-day streak", "Practice 5 days in a row", lambda h, s: s >= 5,
                "silver", "diamond", "Certificate of Consistency"),
    Achievement("streak7", "Weekly habit", "Practice 7 days in a row", lambda h, s: s >= 7, "gold", "diamond"),
    Achievement("streak30", "Unstoppable", "Practice 30 days in a row", lambda h, s: s >= 30, "platinum", "crown"),
    Achievement("daily", "Daily driver", "Complete a Daily Challenge", lambda h, s: (h["mode"] == "daily").any(),
                "bronze", "check"),
    Achievement("drill", "Doctor's orders", "Finish a Key Doctor drill", lambda h, s: (h["mode"] == "drill").any(),
                "bronze", "check"),
)
BY_ID = {a.id: a for a in ACHIEVEMENTS}
STREAK_BADGES = (3, 5, 7, 30)


def unlocked_ids(history: pd.DataFrame) -> set[str]:
    if history.empty:
        return set()
    _, best_streak = streaks(practice_days(history))
    return {a.id for a in ACHIEVEMENTS if a.check(history, best_streak)}


# --------------------------------------------------------------------- weak keys
@dataclass(frozen=True)
class KeyStat:
    key: str
    attempts: int
    errors: int

    @property
    def rate(self) -> float:
        return self.errors / self.attempts if self.attempts else 0.0


def key_stats(aggregate: dict[str, list[int]]) -> list[KeyStat]:
    return [KeyStat(k, int(v[0]), int(v[1])) for k, v in aggregate.items() if v[0] > 0]


def weak_keys(aggregate: dict[str, list[int]], limit: int = 5) -> list[KeyStat]:
    """Keys with enough attempts and at least one error, worst error rate first."""
    weak = [s for s in key_stats(aggregate) if s.attempts >= config.MIN_KEY_ATTEMPTS and s.errors > 0]
    return sorted(weak, key=lambda s: (-s.rate, -s.errors))[:limit]


def next_streak_goal(current: int) -> int:
    """The next streak badge the player is working towards (30 once everything else is done)."""
    for goal in STREAK_BADGES:
        if current < goal:
            return goal
    return STREAK_BADGES[-1]


def earned_dates(history: pd.DataFrame) -> dict[str, date]:
    """Local date on which each unlocked achievement was first earned (binary search over prefixes)."""
    if history.empty:
        return {}
    ordered = history.sort_values("created_at").reset_index(drop=True)
    days = list(to_local(ordered["created_at"]).dt.date)

    def passes(achievement: Achievement, k: int) -> bool:
        _, best = streaks(set(days[:k]))
        return bool(achievement.check(ordered.iloc[:k], best))

    out: dict[str, date] = {}
    for achievement in ACHIEVEMENTS:
        if not passes(achievement, len(ordered)):
            continue
        lo, hi = 1, len(ordered)
        while lo < hi:
            mid = (lo + hi) // 2
            lo, hi = (lo, mid) if passes(achievement, mid) else (mid + 1, hi)
        out[achievement.id] = days[lo - 1]
    return out
