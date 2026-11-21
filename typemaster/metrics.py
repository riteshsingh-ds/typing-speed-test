"""Pure scoring maths. No Streamlit, no I/O - trivially unit-testable.

Definitions (also documented in the README):
  * correct chars   - characters in the typed text that match the passage
                      at the same position
  * mistakes        - typed characters that do not match the passage
  * accuracy        - correct / typed * 100
  * net WPM         - (correct chars / 5) / minutes elapsed
  * raw WPM         - (typed chars / 5) / minutes elapsed
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .config import CHARS_PER_WORD


@dataclass(frozen=True)
class Metrics:
    wpm: float
    raw_wpm: float
    accuracy: float
    correct_chars: int
    incorrect_chars: int
    typed_chars: int
    elapsed_sec: float


def compute_metrics(target: str, typed: str, elapsed_sec: float) -> Metrics:
    """Score ``typed`` against ``target`` after ``elapsed_sec`` seconds."""
    if isinstance(elapsed_sec, bool) or not isinstance(elapsed_sec, (int, float)) \
            or not math.isfinite(elapsed_sec) or elapsed_sec <= 0:
        raise ValueError("elapsed_sec must be a positive, finite number")

    typed = typed[: len(target)]
    typed_chars = len(typed)
    correct = sum(1 for expected, actual in zip(target, typed) if expected == actual)
    incorrect = typed_chars - correct

    minutes = elapsed_sec / 60.0
    wpm = (correct / CHARS_PER_WORD) / minutes
    raw_wpm = (typed_chars / CHARS_PER_WORD) / minutes
    accuracy = (correct / typed_chars * 100.0) if typed_chars else 0.0

    return Metrics(
        wpm=round(wpm, 2),
        raw_wpm=round(raw_wpm, 2),
        accuracy=round(accuracy, 2),
        correct_chars=correct,
        incorrect_chars=incorrect,
        typed_chars=typed_chars,
        elapsed_sec=round(elapsed_sec, 2),
    )


_TIERS = (
    (120, "Legend"),
    (100, "Elite"),
    (80, "Expert"),
    (60, "Fast"),
    (40, "Steady"),
    (20, "Learner"),
    (0, "Warming up"),
)


def speed_tier(wpm: float) -> str:
    """Human-friendly label for a WPM score."""
    for threshold, label in _TIERS:
        if wpm >= threshold:
            return label
    return _TIERS[-1][1]


def char_stats(target: str, typed: str, ever_wrong=()) -> dict[str, list[int]]:
    """Per-key ``[attempts, errors]`` for one test (used by Key Doctor).

    A position counts as an error if the final character is wrong *or* it was ever
    typed wrong before being corrected (``ever_wrong`` comes from the typing engine).
    Letters are folded to lower case; the space bar is stored as ``"space"``.
    """
    wrong = set(ever_wrong)
    stats: dict[str, list[int]] = {}
    for i, (expected, actual) in enumerate(zip(target, typed)):
        key = "space" if expected == " " else expected.lower()
        record = stats.setdefault(key, [0, 0])
        record[0] += 1
        if expected != actual or i in wrong:
            record[1] += 1
    return stats
