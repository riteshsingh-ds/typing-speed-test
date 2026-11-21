"""Key Doctor drills: practice text that over-represents the keys a player misses most."""
from __future__ import annotations

import random
from typing import Optional

from . import config
from .passages import PASSAGES
from .progress import KeyStat

_POOL: tuple[str, ...] = tuple(sorted({
    token.lower() for bank in PASSAGES.values() for passage in bank for token in passage.split()
    if 2 <= len(token) <= 14
}))


def _weight(token: str, weights: dict[str, float]) -> float:
    return sum(weights.get(ch, 0.0) for ch in token.lower())


def build_drill(weak: list[KeyStat], duration: int, rng: Optional[random.Random] = None) -> str:
    """Build a drill of real words/tokens rich in the weak keys (``"space"`` is ignored)."""
    if duration not in config.TARGET_CHARS:
        raise ValueError(f"Unsupported duration: {duration!r}")
    rng = rng or random.Random()
    weights = {s.key: max(s.rate, 0.05) for s in weak if s.key != "space" and len(s.key) == 1}
    scored = [(t, _weight(t, weights)) for t in _POOL]
    rich = [(t, w) for t, w in scored if w > 0]
    if len(rich) < 12:                      # too few matches: pad with random tokens
        rich += [(t, 0.1) for t in rng.sample(_POOL, 40)]
    tokens, weight_list = zip(*rich)

    target, out, length, prev = config.TARGET_CHARS[duration], [], 0, None
    while length - 1 < target:
        token = rng.choices(tokens, weights=weight_list, k=1)[0]
        if token == prev:
            continue
        out.append(token)
        length += len(token) + 1
        prev = token
    return " ".join(out)
