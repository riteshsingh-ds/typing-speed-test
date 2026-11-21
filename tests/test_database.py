import sqlite3

import pytest

from typemaster.database import Database, DatabaseError
from typemaster.metrics import compute_metrics


@pytest.fixture()
def db(tmp_path):
    return Database(tmp_path / "t.db")


def m(wpm_chars=300, elapsed=60, acc_wrong=0):
    typed = "a" * (wpm_chars - acc_wrong) + "b" * acc_wrong
    return compute_metrics("a" * wpm_chars, typed, elapsed)


def test_init_creates_tables(db):
    with sqlite3.connect(db.path) as c:
        names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"players", "results"} <= names


def test_init_is_idempotent(tmp_path):
    Database(tmp_path / "x.db")
    Database(tmp_path / "x.db")


def test_player_case_insensitive(db):
    a = db.get_or_create_player("Ritesh")
    b = db.get_or_create_player("rItEsH")
    assert a.id == b.id and b.name == "Ritesh"
    assert db.get_or_create_player("Other").id != a.id


def test_save_and_history_roundtrip(db):
    p = db.get_or_create_player("Ana")
    rid = db.save_result(p.id, "t1", 60, "Easy", m(), [10.0, 20.0])
    assert isinstance(rid, int)
    h = db.history(p.id)
    assert len(h) == 1
    row = h.iloc[0]
    assert row["wpm"] == 60.0 and row["difficulty"] == "Easy" and row["duration_sec"] == 60
    assert str(h["created_at"].dtype).startswith("datetime64")


def test_duplicate_test_id_is_not_saved_twice(db):
    p = db.get_or_create_player("Ana")
    assert db.save_result(p.id, "same", 60, "Easy", m(), []) is not None
    assert db.save_result(p.id, "same", 60, "Easy", m(), []) is None
    assert len(db.history(p.id)) == 1


def test_constraints_reject_bad_rows(db):
    p = db.get_or_create_player("Ana")
    with pytest.raises(DatabaseError):
        db.save_result(p.id, "bad1", 45, "Easy", m(), [])      # unsupported duration
    with pytest.raises(DatabaseError):
        db.save_result(p.id, "bad2", 60, "Nightmare", m(), [])  # unknown difficulty
    with pytest.raises(DatabaseError):
        db.save_result(9999, "bad3", 60, "Easy", m(), [])       # unknown player (FK)


def test_stats_and_empty_stats(db):
    p = db.get_or_create_player("Ana")
    s = db.stats(p.id)
    assert s["tests"] == 0 and s["best_wpm"] == 0 and s["recent_wpm"] == 0
    db.save_result(p.id, "a", 60, "Easy", m(300), [])
    db.save_result(p.id, "b", 60, "Easy", m(150, acc_wrong=15), [])
    s = db.stats(p.id)
    assert s["tests"] == 2 and s["best_wpm"] == 60.0 and s["mistakes"] == 15
    assert s["avg_wpm"] == pytest.approx((60 + 27) / 2)


def test_personal_best_filters(db):
    p = db.get_or_create_player("Ana")
    assert db.personal_best(p.id) is None
    db.save_result(p.id, "a", 30, "Easy", m(150, 30), [])        # 60 wpm
    db.save_result(p.id, "b", 60, "Hard", m(200, 60), [])        # 40 wpm
    assert db.personal_best(p.id)["wpm"] == 60.0
    assert db.personal_best(p.id, 60, "Hard")["wpm"] == 40.0
    assert db.personal_best(p.id, 120) is None


def test_leaderboard_best_per_player_sorted_and_filtered(db):
    a, b = db.get_or_create_player("Ana"), db.get_or_create_player("Ben")
    db.save_result(a.id, "a1", 60, "Easy", m(300), [])           # 60
    db.save_result(a.id, "a2", 60, "Easy", m(200), [])           # 40
    db.save_result(b.id, "b1", 60, "Easy", m(400), [])           # 80
    db.save_result(b.id, "b2", 30, "Hard", m(100, 30), [])       # 40
    board = db.leaderboard()
    assert list(board["player"]) == ["Ben", "Ana"]
    assert list(board["wpm"]) == [80.0, 60.0]
    hard = db.leaderboard(difficulty="Hard")
    assert list(hard["player"]) == ["Ben"]
    assert db.leaderboard(duration=120).empty
    assert len(db.leaderboard(limit=1)) == 1


def test_delete_history_only_affects_one_player(db):
    a, b = db.get_or_create_player("Ana"), db.get_or_create_player("Ben")
    db.save_result(a.id, "a1", 60, "Easy", m(), [])
    db.save_result(b.id, "b1", 60, "Easy", m(), [])
    assert db.delete_history(a.id) == 1
    assert db.history(a.id).empty and len(db.history(b.id)) == 1


# ---------------------------------------------------------------- v2 features
def test_old_database_is_migrated(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as c:
        c.executescript("""
            CREATE TABLE players (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE COLLATE NOCASE, created_at TEXT NOT NULL);
            CREATE TABLE results (id INTEGER PRIMARY KEY AUTOINCREMENT, test_id TEXT NOT NULL UNIQUE,
              player_id INTEGER NOT NULL, duration_sec INTEGER NOT NULL, difficulty TEXT NOT NULL, wpm REAL NOT NULL,
              raw_wpm REAL NOT NULL, accuracy REAL NOT NULL, correct_chars INTEGER NOT NULL, incorrect_chars INTEGER NOT NULL,
              typed_chars INTEGER NOT NULL, elapsed_sec REAL NOT NULL, wpm_series TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL);
            INSERT INTO players VALUES (1, 'Old', '2026-01-01T00:00:00+00:00');
            INSERT INTO results VALUES (1, 't', 1, 60, 'Easy', 50, 55, 95, 250, 10, 260, 60, '[]', '2026-01-02T00:00:00+00:00');
        """)
    db = Database(path)
    h = db.history(1)
    assert len(h) == 1 and h.iloc[0]["mode"] == "standard" and db.stats(1)["best_wpm"] == 50
    assert db.save_result(1, "new", 60, "Easy", m(), [], mode="daily", challenge_date="2026-11-20") is not None
    Database(path)  # second init must not fail on already-migrated columns


def test_drills_are_excluded_from_records_and_boards(db):
    p = db.get_or_create_player("Ana")
    db.save_result(p.id, "s", 60, "Medium", m(200), [])                  # 40 wpm
    db.save_result(p.id, "d", 60, "Medium", m(600), [], mode="drill")    # 120 wpm drill
    assert db.personal_best(p.id)["wpm"] == 40.0
    assert db.stats(p.id)["best_wpm"] == 40.0 and db.stats(p.id)["tests"] == 2
    assert list(db.leaderboard()["wpm"]) == [40.0]
    assert db.platform_stats()["top_wpm"] == 40.0


def test_daily_board_and_best(db):
    a, b = db.get_or_create_player("Ana"), db.get_or_create_player("Ben")
    db.save_result(a.id, "a1", 60, "Medium", m(200), [], mode="daily", challenge_date="2026-11-20")
    db.save_result(a.id, "a2", 60, "Medium", m(300), [], mode="daily", challenge_date="2026-11-20")
    db.save_result(b.id, "b1", 60, "Medium", m(250), [], mode="daily", challenge_date="2026-11-20")
    db.save_result(b.id, "b2", 60, "Medium", m(500), [], mode="daily", challenge_date="2026-11-19")
    board = db.daily_leaderboard("2026-11-20")
    assert list(board["player"]) == ["Ana", "Ben"] and list(board["wpm"]) == [60.0, 50.0]
    assert db.daily_best(a.id, "2026-11-20")["wpm"] == 60.0 and db.daily_best(a.id, "2026-11-21") is None
    assert db.platform_stats("2026-11-20")["daily_players"] == 2


def test_key_stats_aggregate_and_ghost_series(db):
    p = db.get_or_create_player("Ana")
    db.save_result(p.id, "k1", 60, "Easy", m(), [10, 20], char_stats={"a": [10, 2], "space": [5, 0]})
    db.save_result(p.id, "k2", 60, "Easy", m(200), [5, 6], char_stats={"a": [10, 1], "b": [4, 4]})
    assert db.key_stats(p.id) == {"a": [20, 3], "space": [5, 0], "b": [4, 4]}
    assert db.best_series(p.id, 60, "Easy") == [10.0, 20.0]          # the faster run is the ghost
    assert db.best_series(p.id, 30, "Easy") == []
