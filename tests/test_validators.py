import pytest

from typemaster.validators import ValidationError, validate_player_name, validate_submission

TEST = {"id": "abc123", "text": "hello world, this is a test", "duration": 60, "difficulty": "Easy"}


def ok_payload(**over):
    p = {"test_id": "abc123", "typed": "hello", "elapsed_ms": 5000, "series": [10, 20]}
    p.update(over)
    return p


@pytest.mark.parametrize("raw,expected", [("  Ritesh  ", "Ritesh"), ("a  b", "a b"), ("Ana_Maria-2.0", "Ana_Maria-2.0")])
def test_valid_names(raw, expected):
    assert validate_player_name(raw) == expected


@pytest.mark.parametrize("raw", ["", " ", "a", "x" * 21, "<script>", "bad;name", None, 5, "-dash"])
def test_invalid_names(raw):
    with pytest.raises(ValidationError):
        validate_player_name(raw)


def test_valid_submission():
    s = validate_submission(ok_payload(), TEST)
    assert s.typed == "hello" and s.elapsed_sec == 5.0 and s.series == [10.0, 20.0]


def test_wrong_test_id():
    with pytest.raises(ValidationError):
        validate_submission(ok_payload(test_id="other"), TEST)


@pytest.mark.parametrize("payload", [None, "x", [], {}, ok_payload(typed=5), ok_payload(typed="")])
def test_malformed_or_empty(payload):
    with pytest.raises(ValidationError):
        validate_submission(payload, TEST)


def test_typed_longer_than_text():
    with pytest.raises(ValidationError):
        validate_submission(ok_payload(typed="x" * 500), TEST)


@pytest.mark.parametrize("ms", [None, "5000", True, float("nan"), 100, 0, -5])
def test_bad_elapsed(ms):
    with pytest.raises(ValidationError):
        validate_submission(ok_payload(elapsed_ms=ms), TEST)


def test_elapsed_slightly_over_is_clamped():
    s = validate_submission(ok_payload(elapsed_ms=61500), TEST)
    assert s.elapsed_sec == 60.0


def test_elapsed_way_over_rejected():
    with pytest.raises(ValidationError):
        validate_submission(ok_payload(elapsed_ms=90000), TEST)


def test_series_sanitised():
    s = validate_submission(ok_payload(series=[10, "x", None, True, 9999, -4, float("inf"), 33.33]), TEST)
    assert s.series == [10.0, 350.0, 0.0, 33.3]
    assert validate_submission(ok_payload(series="nope"), TEST).series == []
