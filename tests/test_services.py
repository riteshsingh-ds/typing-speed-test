import pytest

from typemaster import config
from typemaster.database import Database
from typemaster.services import process_submission, retry_save

TEXT = "the quick brown fox jumps over the lazy dog " * 10


@pytest.fixture()
def env(tmp_path):
    db = Database(tmp_path / "s.db")
    player = db.get_or_create_player("Ana")
    return db, player


def make_test(tid="t1", duration=60):
    return {"id": tid, "text": TEXT, "duration": duration, "difficulty": "Easy"}


def payload(tid="t1", typed=None, ms=60000, series=None):
    return {"test_id": tid, "typed": TEXT[:300] if typed is None else typed, "elapsed_ms": ms, "series": series or [50, 60]}


def test_happy_path_scores_and_saves(env):
    db, p = env
    r = process_submission(db, p.id, make_test(), payload())
    assert r.error is None and r.saved and r.pb_status == "first"
    assert r.metrics.wpm == 60.0 and r.metrics.accuracy == 100.0
    assert len(db.history(p.id)) == 1


def test_server_recomputes_and_ignores_client_claims(env):
    db, p = env
    pl = payload()
    pl["client"] = {"wpm": 999, "accuracy": 100}
    r = process_submission(db, p.id, make_test(), pl)
    assert r.metrics.wpm == 60.0


def test_duplicate_submission_not_saved_twice(env):
    db, p = env
    first = process_submission(db, p.id, make_test(), payload())
    second = process_submission(db, p.id, make_test(), payload())
    assert first.saved and second.duplicate and not second.saved
    assert len(db.history(p.id)) == 1


def test_mistakes_counted(env):
    db, p = env
    typed = "X" + TEXT[1:300]
    r = process_submission(db, p.id, make_test(), payload(typed=typed))
    assert r.metrics.incorrect_chars == 1 and r.metrics.correct_chars == 299
    assert r.metrics.accuracy == pytest.approx(99.67, abs=0.01)


def test_personal_best_progression(env):
    db, p = env
    r1 = process_submission(db, p.id, make_test("a"), payload("a", typed=TEXT[:200]))
    r2 = process_submission(db, p.id, make_test("b"), payload("b", typed=TEXT[:300]))
    r3 = process_submission(db, p.id, make_test("c"), payload("c", typed=TEXT[:100]))
    assert (r1.pb_status, r2.pb_status, r3.pb_status) == ("first", "overall", None)
    r4 = process_submission(db, p.id, make_test("d", 30), payload("d", typed=TEXT[:50], ms=30000))
    assert r4.pb_status == "category"   # first 30s Easy result, but below the overall best


@pytest.mark.parametrize("bad", [
    {"typed": ""}, {"elapsed_ms": 10}, {"test_id": "nope"}, {"elapsed_ms": 999999},
])
def test_invalid_payload_is_rejected_not_saved(env, bad):
    db, p = env
    pl = payload()
    pl.update(bad)
    r = process_submission(db, p.id, make_test(), pl)
    assert r.error and r.metrics is None and not r.saved
    assert db.history(p.id).empty


def test_implausible_speed_rejected(env):
    db, p = env
    r = process_submission(db, p.id, make_test(), payload(typed=TEXT[:400], ms=1000))
    assert r.error and "plausible" in r.error
    assert db.history(p.id).empty
    assert config.MAX_PLAUSIBLE_WPM == 350


def test_database_failure_keeps_result_and_retry_works(env, monkeypatch):
    db, p = env
    from typemaster.database import DatabaseError
    original = db.save_result

    def boom(*a, **k):
        raise DatabaseError("disk is full")

    monkeypatch.setattr(db, "save_result", boom)
    r = process_submission(db, p.id, make_test(), payload())
    assert r.metrics is not None and r.save_error == "disk is full" and not r.saved

    monkeypatch.setattr(db, "save_result", original)
    r = retry_save(db, p.id, r)
    assert r.saved and r.save_error is None
    assert len(db.history(p.id)) == 1
    assert retry_save(db, p.id, r).saved   # idempotent


def test_progress_fields_and_char_stats_saved(env):
    db, p = env
    pl = payload(typed="X" + TEXT[1:300])
    pl["ever_wrong"] = [0, 5, 9999, "x", -1]
    r = process_submission(db, p.id, make_test(), pl)
    assert r.saved and r.xp_gain > 0 and "First keystrokes" in r.new_badges
    assert r.char_stats["t"] == [r.char_stats["t"][0], 1]            # position 0 wrong
    assert db.key_stats(p.id)["t"][1] >= 1


def test_drill_never_sets_records_and_daily_is_tagged(env):
    db, p = env
    drill = dict(make_test("d1"), mode="drill")
    r = process_submission(db, p.id, drill, payload("d1"))
    assert r.saved and r.pb_status is None and db.personal_best(p.id) is None
    daily = dict(make_test("d2"), mode="daily", challenge_date="2026-11-20")
    r = process_submission(db, p.id, daily, payload("d2"))
    assert r.pb_status == "first" and db.daily_best(p.id, "2026-11-20")["wpm"] == 60.0


def test_ghost_is_previous_best_and_level_up(env):
    db, p = env
    process_submission(db, p.id, make_test("g1"), payload("g1", series=[10, 20, 30]))
    r = process_submission(db, p.id, make_test("g2"), payload("g2", series=[1, 2]))
    assert r.ghost == [10.0, 20.0, 30.0]
    big = process_submission(db, p.id, make_test("g3", 120), payload("g3", typed=TEXT[:430], ms=120000))
    assert big.saved and (big.level_up is None or big.level_up >= 2)
