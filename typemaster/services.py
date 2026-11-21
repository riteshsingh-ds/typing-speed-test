"""Business logic that turns a raw browser payload into a saved, scored result.

Kept free of Streamlit imports so it can be unit-tested directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from . import config, progress
from .database import Database, DatabaseError
from .metrics import Metrics, char_stats, compute_metrics
from .validators import ValidationError, validate_submission


@dataclass
class TestResult:
    __test__ = False  # stop pytest trying to collect this class

    test_id: str
    duration: int
    difficulty: str
    mode: str = "standard"
    challenge_date: Optional[str] = None
    metrics: Optional[Metrics] = None
    series: list[float] = field(default_factory=list)
    ghost: list[float] = field(default_factory=list)   # pace of the previous best run
    char_stats: dict[str, list[int]] = field(default_factory=dict)
    error: Optional[str] = None          # validation failure: nothing was scored
    save_error: Optional[str] = None     # scored, but the database write failed
    saved: bool = False
    duplicate: bool = False              # this test_id had already been stored
    pb_status: Optional[str] = None      # "first" | "overall" | "category" | None
    result_id: Optional[int] = None
    xp_gain: int = 0
    level_up: Optional[int] = None       # new level number if this test levelled the player up
    new_badges: list[str] = field(default_factory=list)
    new_badge_ids: list[str] = field(default_factory=list)


def _pb_status(db: Database, player_id: int, wpm: float, duration: int, difficulty: str) -> Optional[str]:
    overall = db.personal_best(player_id)
    if overall is None:
        return "first"
    if wpm > overall["wpm"]:
        return "overall"
    category = db.personal_best(player_id, duration, difficulty)
    if category is None or wpm > category["wpm"]:
        return "category"
    return None


def _store(db: Database, player_id: int, result: TestResult) -> Optional[int]:
    return db.save_result(
        player_id, result.test_id, result.duration, result.difficulty, result.metrics, result.series,
        mode=result.mode, challenge_date=result.challenge_date, char_stats=result.char_stats,
    )


def process_submission(
    db: Database, player_id: int, test: Mapping[str, Any], payload: Any
) -> TestResult:
    """Validate, score and store a finished test. Never raises for bad input."""
    result = TestResult(
        test_id=test["id"], duration=test["duration"], difficulty=test["difficulty"],
        mode=test.get("mode", "standard"), challenge_date=test.get("challenge_date"),
    )

    try:
        submission = validate_submission(payload, test)
        metrics = compute_metrics(test["text"], submission.typed, submission.elapsed_sec)
    except (ValidationError, ValueError) as exc:
        result.error = str(exc)
        return result

    if metrics.wpm > config.MAX_PLAUSIBLE_WPM:
        result.error = (
            f"{metrics.wpm:.0f} WPM is faster than humanly plausible, so this run was not saved. "
            "Pasting or automated input is not allowed."
        )
        return result

    result.metrics = metrics
    result.series = submission.series
    result.char_stats = char_stats(test["text"], submission.typed, submission.ever_wrong)
    competitive = result.mode != "drill"

    try:
        before = db.history(player_id)
        if competitive:
            result.pb_status = _pb_status(db, player_id, metrics.wpm, test["duration"], test["difficulty"])
            result.ghost = db.best_series(player_id, test["duration"], test["difficulty"])
        result_id = _store(db, player_id, result)
        if result_id is None:
            result.pb_status = None
            result.duplicate = True
            return result
        result.saved, result.result_id = True, result_id
        after = db.history(player_id)
    except DatabaseError as exc:
        result.save_error = str(exc)
        result.pb_status = None
        return result

    result.xp_gain = progress.xp_for_result(metrics.correct_chars, metrics.accuracy)
    old_level = progress.level_info(progress.total_xp(before)).level
    new_level = progress.level_info(progress.total_xp(after)).level
    if new_level > old_level:
        result.level_up = new_level
    names = {a.id: a.name for a in progress.ACHIEVEMENTS}
    result.new_badge_ids = sorted(progress.unlocked_ids(after) - progress.unlocked_ids(before))
    result.new_badges = [names[i] for i in result.new_badge_ids]
    return result


def retry_save(db: Database, player_id: int, result: TestResult) -> TestResult:
    """Try again to store a result whose first save failed."""
    if result.metrics is None or result.saved or result.duplicate:
        return result
    try:
        result_id = _store(db, player_id, result)
    except DatabaseError as exc:
        result.save_error = str(exc)
        return result
    result.save_error = None
    if result_id is None:
        result.duplicate = True
    else:
        result.saved = True
        result.result_id = result_id
        result.xp_gain = progress.xp_for_result(result.metrics.correct_chars, result.metrics.accuracy)
    return result
