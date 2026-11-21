import random

import pytest

from typemaster import config
from typemaster.passages import PASSAGES, build_challenge


def test_all_difficulties_have_enough_unique_passages():
    assert set(PASSAGES) == set(config.DIFFICULTIES)
    for bank in PASSAGES.values():
        assert len(bank) >= 8 and len(set(bank)) == len(bank)


def test_passages_are_clean_ascii():
    for bank in PASSAGES.values():
        for p in bank:
            assert p.isascii() and p.isprintable()
            assert p == p.strip() and "  " not in p
            assert 200 <= len(p) <= 450


@pytest.mark.parametrize("difficulty", config.DIFFICULTIES)
@pytest.mark.parametrize("duration", config.DURATIONS)
def test_text_long_enough_and_no_repeats(difficulty, duration):
    c = build_challenge(difficulty, duration, rng=random.Random(1))
    assert len(c.text) >= config.TARGET_CHARS[duration]
    for p in PASSAGES[difficulty]:
        assert c.text.count(p) <= 1


def test_randomness_and_avoid_first():
    texts = {build_challenge("Easy", 30, rng=random.Random(s)).text for s in range(20)}
    assert len(texts) > 5
    for seed in range(30):
        c = build_challenge("Medium", 30, rng=random.Random(seed), avoid_first=3)
        assert c.first_index != 3


def test_invalid_arguments():
    with pytest.raises(ValueError):
        build_challenge("Insane", 60)
    with pytest.raises(ValueError):
        build_challenge("Easy", 45)
