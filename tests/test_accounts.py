"""Accounts: email identity, duplicate display names, claim flow, migration from the name-only v1 schema."""
import sqlite3

import pytest

from typemaster.database import Database
from typemaster.metrics import compute_metrics
from typemaster.utils import board_labels


@pytest.fixture()
def db(tmp_path):
    return Database(tmp_path / "a.db")


def m(chars=300):
    return compute_metrics("a" * chars, "a" * chars, 60)


def test_many_players_can_share_a_display_name(db):
    a = db.create_account("Ritesh", "a@example.com")
    b = db.create_account("Ritesh", "b@example.com")
    assert a.id != b.id and a.name == b.name == "Ritesh"
    assert db.get_player_by_email("A@Example.com").id == a.id        # email lookup is case-insensitive


def test_email_is_unique_and_create_is_idempotent(db):
    a = db.create_account("One", "x@example.com")
    again = db.create_account("Other name", "X@example.com")
    assert again.id == a.id and again.name == "One"


def test_claim_attaches_email_once(db):
    old = db.get_or_create_player("Legacy")
    db.save_result(old.id, "t", 60, "Easy", m(), [])
    found = db.find_unclaimed("legacy")
    assert [f["id"] for f in found] == [old.id] and found[0]["tests"] == 1 and found[0]["best_wpm"] == 60.0
    assert db.claim_player(old.id, "Me@Example.com") is True
    assert db.get_player_by_email("me@example.com").id == old.id
    assert db.claim_player(old.id, "thief@example.com") is False      # already claimed: cannot be stolen
    assert db.find_unclaimed("Legacy") == []
    assert len(db.history(old.id)) == 1                                # scores kept


def test_one_email_cannot_claim_two_profiles(db):
    a, b = db.get_or_create_player("A"), db.get_or_create_player("B")
    assert db.claim_player(a.id, "same@example.com")
    assert db.claim_player(b.id, "same@example.com") is False


def test_local_mode_reuses_unclaimed_but_not_claimed_profiles(db):
    first = db.get_or_create_player("Sam")
    assert db.get_or_create_player("sam").id == first.id
    db.claim_player(first.id, "sam@example.com")
    assert db.get_or_create_player("Sam").id != first.id               # claimed profiles are private


def test_rename_and_delete_account_cascades(db):
    p = db.create_account("Old", "d@example.com")
    db.save_result(p.id, "t1", 60, "Easy", m(), [])
    db.rename_player(p.id, "New")
    assert db.get_player(p.id).name == "New"
    db.delete_player(p.id)
    assert db.get_player(p.id) is None and db.history(p.id).empty
    assert db.create_account("Again", "d@example.com").id != p.id       # email is free again


def test_board_labels_disambiguate_duplicate_names(db):
    a, b, c = (db.create_account("Ritesh", "a@x.com"), db.create_account("Ritesh", "b@x.com"),
               db.create_account("Zoe", "z@x.com"))
    for i, (p, chars) in enumerate([(a, 400), (b, 300), (c, 200)]):
        db.save_result(p.id, f"t{i}", 60, "Easy", m(chars), [])
    board = db.leaderboard()
    labels = board_labels(board, me_id=b.id)
    assert labels == [f"Ritesh #{a.id}", f"Ritesh #{b.id} (you)", "Zoe"]
    assert board_labels(board.iloc[0:0]) == []


def test_v1_database_is_migrated_without_losing_scores(tmp_path):
    path = tmp_path / "v1.db"
    with sqlite3.connect(path) as c:
        c.executescript("""
            CREATE TABLE players (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE COLLATE NOCASE, created_at TEXT NOT NULL);
            CREATE TABLE results (id INTEGER PRIMARY KEY AUTOINCREMENT, test_id TEXT NOT NULL UNIQUE,
              player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE, duration_sec INTEGER NOT NULL,
              difficulty TEXT NOT NULL, wpm REAL NOT NULL, raw_wpm REAL NOT NULL, accuracy REAL NOT NULL,
              correct_chars INTEGER NOT NULL, incorrect_chars INTEGER NOT NULL, typed_chars INTEGER NOT NULL,
              elapsed_sec REAL NOT NULL, wpm_series TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL);
            INSERT INTO players VALUES (1, 'Ritesh Singh', '2026-11-01T00:00:00+00:00'), (2, 'Ana', '2026-11-02T00:00:00+00:00');
            INSERT INTO results VALUES (1, 't1', 1, 30, 'Easy', 21, 22, 88.1, 100, 12, 112, 30, '[]', '2026-11-21T10:00:00+00:00');
        """)
    db = Database(path)
    assert db.get_player(1).name == "Ritesh Singh" and db.get_player(1).email is None
    assert len(db.history(1)) == 1 and db.stats(1)["best_wpm"] == 21
    # the UNIQUE(name) constraint is gone, accounts work, and the old profile can be claimed
    assert db.create_account("Ritesh Singh", "new@example.com").id not in (1, 2)
    assert db.claim_player(1, "ritesh@example.com")
    assert db.get_player_by_email("ritesh@example.com").id == 1 and len(db.history(1)) == 1
    Database(path)                                                    # re-running init is a no-op
    with sqlite3.connect(path) as c:
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []
