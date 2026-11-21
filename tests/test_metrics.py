import pytest

from typemaster.metrics import compute_metrics, speed_tier


def test_perfect_typing():
    m = compute_metrics("hello world", "hello world", 60)
    assert m.correct_chars == 11 and m.incorrect_chars == 0
    assert m.accuracy == 100.0
    assert m.wpm == pytest.approx(2.2)          # 11 chars / 5 per minute


def test_mistakes_and_accuracy():
    m = compute_metrics("hello", "hexlo", 60)
    assert (m.correct_chars, m.incorrect_chars, m.typed_chars) == (4, 1, 5)
    assert m.accuracy == 80.0
    assert m.wpm == pytest.approx(0.8)
    assert m.raw_wpm == pytest.approx(1.0)


def test_known_wpm_value():
    target = "a" * 300
    m = compute_metrics(target, target, 60)       # 300 chars = 60 words in one minute
    assert m.wpm == 60.0 and m.raw_wpm == 60.0


def test_elapsed_scaling():
    target = "a" * 150
    assert compute_metrics(target, target, 30).wpm == 60.0   # 30 words in 30s
    assert compute_metrics(target, target, 120).wpm == 15.0


def test_typed_longer_than_target_is_clipped():
    m = compute_metrics("abc", "abcdef", 60)
    assert m.typed_chars == 3 and m.correct_chars == 3


def test_empty_typed():
    m = compute_metrics("abc", "", 10)
    assert m.accuracy == 0.0 and m.wpm == 0.0 and m.typed_chars == 0


@pytest.mark.parametrize("bad", [0, -1, float("nan"), float("inf"), True, "5"])
def test_invalid_elapsed(bad):
    with pytest.raises(ValueError):
        compute_metrics("abc", "abc", bad)


def test_tiers():
    assert speed_tier(5) == "Warming up"
    assert speed_tier(45) == "Steady"
    assert speed_tier(120) == "Legend"
