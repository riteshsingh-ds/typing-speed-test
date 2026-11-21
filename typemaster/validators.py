"""Input validation for player names and results coming from the browser."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from . import config


class ValidationError(ValueError):
    """Raised with a message that is safe to show to the user."""


_NAME_RE = re.compile(r"^\w[\w .\-]*$")


def validate_player_name(raw: Any) -> str:
    """Return a cleaned player name or raise :class:`ValidationError`."""
    if not isinstance(raw, str):
        raise ValidationError("Please enter a name.")
    name = " ".join(raw.split())
    if len(name) < config.NAME_MIN:
        raise ValidationError(f"Your name needs at least {config.NAME_MIN} characters.")
    if len(name) > config.NAME_MAX:
        raise ValidationError(f"Your name can be at most {config.NAME_MAX} characters.")
    if not _NAME_RE.match(name):
        raise ValidationError("Use letters, numbers, spaces, '.', '-' or '_' only.")
    return name


@dataclass(frozen=True)
class Submission:
    typed: str
    elapsed_sec: float
    series: list[float]
    ever_wrong: list[int] = field(default_factory=list)


def _clean_series(raw: Any) -> list[float]:
    if not isinstance(raw, list):
        return []
    cleaned: list[float] = []
    for value in raw[: config.MAX_SERIES_POINTS]:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if not math.isfinite(value):
            continue
        cleaned.append(round(min(max(float(value), 0.0), float(config.MAX_PLAUSIBLE_WPM)), 1))
    return cleaned


def _clean_wrong(raw: Any, limit: int) -> list[int]:
    if not isinstance(raw, list):
        return []
    seen = {v for v in raw[: config.MAX_WRONG_INDEXES]
            if isinstance(v, int) and not isinstance(v, bool) and 0 <= v < limit}
    return sorted(seen)


def validate_submission(payload: Any, test: Mapping[str, Any]) -> Submission:
    """Validate the result sent by the typing engine for the active ``test``."""
    if not isinstance(payload, dict):
        raise ValidationError("The result data was malformed, so it was not saved.")
    if payload.get("test_id") != test["id"]:
        raise ValidationError("That result belongs to a different test and was ignored.")

    typed = payload.get("typed")
    if not isinstance(typed, str):
        raise ValidationError("The result data was malformed, so it was not saved.")
    if len(typed) > len(test["text"]):
        raise ValidationError("More characters were typed than the passage contains.")
    if not typed:
        raise ValidationError("No typing was detected, so this test was not scored.")

    elapsed_ms = payload.get("elapsed_ms")
    if isinstance(elapsed_ms, bool) or not isinstance(elapsed_ms, (int, float)) or not math.isfinite(elapsed_ms):
        raise ValidationError("The timing data was missing, so the test was not scored.")

    elapsed = float(elapsed_ms) / 1000.0
    limit = float(test["duration"])
    if elapsed > limit + config.ELAPSED_TOLERANCE_SEC:
        raise ValidationError("The timing data looked wrong, so the test was not saved.")
    elapsed = min(elapsed, limit)
    if elapsed < config.MIN_ELAPSED_SEC:
        raise ValidationError("That run was too short to score. Keep typing for at least a second.")

    return Submission(typed=typed, elapsed_sec=elapsed, series=_clean_series(payload.get("series")),
                      ever_wrong=_clean_wrong(payload.get("ever_wrong"), len(typed)))
