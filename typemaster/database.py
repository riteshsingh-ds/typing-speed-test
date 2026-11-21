"""SQLite persistence layer.

A fresh connection is opened per operation, which keeps the class safe to share
between Streamlit's script threads. ``test_id`` is UNIQUE, so a score can never
be stored twice even if the UI misbehaves. Older databases are upgraded in place.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

import pandas as pd

from . import config
from .metrics import Metrics


class DatabaseError(RuntimeError):
    """Wraps sqlite3 errors with a message that is safe to show to the user."""


@dataclass(frozen=True)
class Player:
    id: int
    name: str


_DURATIONS_SQL = ",".join(str(d) for d in config.DURATIONS)
_DIFFICULTIES_SQL = ",".join(f"'{d}'" for d in config.DIFFICULTIES)
_MODES_SQL = ",".join(f"'{m}'" for m in config.MODES)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS players (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id          TEXT    NOT NULL UNIQUE,
    player_id        INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    duration_sec     INTEGER NOT NULL CHECK (duration_sec IN ({_DURATIONS_SQL})),
    difficulty       TEXT    NOT NULL CHECK (difficulty IN ({_DIFFICULTIES_SQL})),
    wpm              REAL    NOT NULL CHECK (wpm >= 0),
    raw_wpm          REAL    NOT NULL CHECK (raw_wpm >= 0),
    accuracy         REAL    NOT NULL CHECK (accuracy BETWEEN 0 AND 100),
    correct_chars    INTEGER NOT NULL CHECK (correct_chars >= 0),
    incorrect_chars  INTEGER NOT NULL CHECK (incorrect_chars >= 0),
    typed_chars      INTEGER NOT NULL CHECK (typed_chars > 0),
    elapsed_sec      REAL    NOT NULL CHECK (elapsed_sec > 0),
    wpm_series       TEXT    NOT NULL DEFAULT '[]',
    created_at       TEXT    NOT NULL,
    mode             TEXT    NOT NULL DEFAULT 'standard' CHECK (mode IN ({_MODES_SQL})),
    challenge_date   TEXT,
    mistakes_json    TEXT    NOT NULL DEFAULT '{{}}'
);
"""

# Columns added after v1.0 - applied to older databases by ``_migrate``.
_MIGRATIONS = {
    "mode": f"ALTER TABLE results ADD COLUMN mode TEXT NOT NULL DEFAULT 'standard' CHECK (mode IN ({_MODES_SQL}))",
    "challenge_date": "ALTER TABLE results ADD COLUMN challenge_date TEXT",
    "mistakes_json": "ALTER TABLE results ADD COLUMN mistakes_json TEXT NOT NULL DEFAULT '{}'",
}

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_results_player_time ON results (player_id, created_at);
CREATE INDEX IF NOT EXISTS idx_results_wpm ON results (wpm DESC);
CREATE INDEX IF NOT EXISTS idx_results_daily ON results (mode, challenge_date, wpm DESC);
"""

HISTORY_COLUMNS = [
    "id", "created_at", "duration_sec", "difficulty", "wpm", "raw_wpm", "accuracy",
    "correct_chars", "incorrect_chars", "typed_chars", "elapsed_sec", "mode", "challenge_date",
]
LEADERBOARD_COLUMNS = ["player", "wpm", "accuracy", "duration_sec", "difficulty", "created_at"]
COMPETITIVE = "mode IN ('standard', 'daily')"   # Key Doctor drills never reach records or boards


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _frame(rows: list[sqlite3.Row], columns: list[str]) -> pd.DataFrame:
    df = pd.DataFrame([tuple(r) for r in rows], columns=columns)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    return df


_RANKED_SQL = """WITH ranked AS (
       SELECT r.player_id, r.wpm, r.accuracy, r.duration_sec, r.difficulty, r.created_at,
              ROW_NUMBER() OVER (PARTITION BY r.player_id
                                 ORDER BY r.wpm DESC, r.accuracy DESC, r.created_at ASC) AS rn
       FROM results r
       WHERE {where}
   )
   SELECT p.name AS player, ranked.wpm, ranked.accuracy, ranked.duration_sec,
          ranked.difficulty, ranked.created_at
   FROM ranked JOIN players p ON p.id = ranked.player_id
   WHERE ranked.rn = 1
   ORDER BY ranked.wpm DESC, ranked.accuracy DESC, ranked.created_at ASC
   LIMIT :limit"""


class Database:
    def __init__(self, path: str | Path = config.DB_PATH) -> None:
        self.path = Path(path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatabaseError(f"Cannot create the data folder {self.path.parent}: {exc}") from exc
        self.init()

    # ------------------------------------------------------------------ plumbing
    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        try:
            conn = sqlite3.connect(self.path, timeout=15)
        except sqlite3.Error as exc:
            raise DatabaseError(f"Could not open the database at {self.path}: {exc}") from exc
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise DatabaseError(f"Database error: {exc}") from exc
        finally:
            conn.close()

    def init(self) -> None:
        """Create tables, upgrade older databases and create indexes."""
        with self.connect() as conn:
            try:
                conn.execute("PRAGMA journal_mode = WAL")
            except sqlite3.Error:
                pass  # WAL is a nice-to-have (e.g. unsupported on some network drives)
            conn.executescript(SCHEMA)
            existing = {row["name"] for row in conn.execute("PRAGMA table_info(results)")}
            for column, statement in _MIGRATIONS.items():
                if column not in existing:
                    conn.execute(statement)
            conn.executescript(INDEXES)

    # ------------------------------------------------------------------ players
    def get_or_create_player(self, name: str) -> Player:
        with self.connect() as conn:
            conn.execute("INSERT OR IGNORE INTO players (name, created_at) VALUES (?, ?)", (name, _now()))
            row = conn.execute("SELECT id, name FROM players WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
        return Player(id=row["id"], name=row["name"])

    def get_player(self, player_id: int) -> Optional[Player]:
        with self.connect() as conn:
            row = conn.execute("SELECT id, name FROM players WHERE id = ?", (player_id,)).fetchone()
        return Player(id=row["id"], name=row["name"]) if row else None

    # ------------------------------------------------------------------ results
    def save_result(
        self,
        player_id: int,
        test_id: str,
        duration_sec: int,
        difficulty: str,
        metrics: Metrics,
        series: list[float],
        mode: str = "standard",
        challenge_date: Optional[str] = None,
        char_stats: Optional[dict[str, list[int]]] = None,
    ) -> Optional[int]:
        """Insert a result. Returns its id, or ``None`` if ``test_id`` was already saved."""
        with self.connect() as conn:
            try:
                cur = conn.execute(
                    """INSERT INTO results
                       (test_id, player_id, duration_sec, difficulty, wpm, raw_wpm, accuracy,
                        correct_chars, incorrect_chars, typed_chars, elapsed_sec, wpm_series, created_at,
                        mode, challenge_date, mistakes_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        test_id, player_id, duration_sec, difficulty, metrics.wpm, metrics.raw_wpm,
                        metrics.accuracy, metrics.correct_chars, metrics.incorrect_chars,
                        metrics.typed_chars, metrics.elapsed_sec, json.dumps(series), _now(),
                        mode, challenge_date, json.dumps(char_stats or {}),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                if "test_id" in str(exc):
                    return None  # duplicate submission - already stored
                raise
            return int(cur.lastrowid)

    def history(self, player_id: int) -> pd.DataFrame:
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT {', '.join(HISTORY_COLUMNS)} FROM results WHERE player_id = ? "
                "ORDER BY created_at DESC, id DESC",
                (player_id,),
            ).fetchall()
        return _frame(rows, HISTORY_COLUMNS)

    def stats(self, player_id: int) -> dict[str, Any]:
        """Lifetime numbers. Speed/accuracy figures ignore Key Doctor drills."""
        with self.connect() as conn:
            row = conn.execute(
                f"""SELECT COUNT(*)                                            AS tests,
                          COALESCE(AVG(CASE WHEN {COMPETITIVE} THEN wpm END), 0)       AS avg_wpm,
                          COALESCE(MAX(CASE WHEN {COMPETITIVE} THEN wpm END), 0)       AS best_wpm,
                          COALESCE(AVG(CASE WHEN {COMPETITIVE} THEN accuracy END), 0)  AS avg_accuracy,
                          COALESCE(MAX(CASE WHEN {COMPETITIVE} THEN accuracy END), 0)  AS best_accuracy,
                          COALESCE(SUM(incorrect_chars), 0)                    AS mistakes,
                          COALESCE(SUM(elapsed_sec), 0)                        AS seconds,
                          (SELECT AVG(wpm) FROM (SELECT wpm FROM results WHERE player_id = ? AND {COMPETITIVE}
                                                 ORDER BY created_at DESC, id DESC LIMIT 10)) AS recent_wpm
                   FROM results WHERE player_id = ?""",
                (player_id, player_id),
            ).fetchone()
        stats = dict(row)
        stats["recent_wpm"] = stats["recent_wpm"] or 0.0
        return stats

    def personal_best(
        self, player_id: int, duration: Optional[int] = None, difficulty: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                f"""SELECT wpm, accuracy, duration_sec, difficulty, created_at FROM results
                   WHERE player_id = :pid AND {COMPETITIVE}
                     AND (:dur  IS NULL OR duration_sec = :dur)
                     AND (:diff IS NULL OR difficulty   = :diff)
                   ORDER BY wpm DESC, accuracy DESC, created_at ASC LIMIT 1""",
                {"pid": player_id, "dur": duration, "diff": difficulty},
            ).fetchone()
        return dict(row) if row else None

    def best_series(self, player_id: int, duration: int, difficulty: str) -> list[float]:
        """Per-second pace of the player's best run for a setup (the 'ghost')."""
        with self.connect() as conn:
            row = conn.execute(
                f"""SELECT wpm_series FROM results
                   WHERE player_id = ? AND duration_sec = ? AND difficulty = ? AND {COMPETITIVE}
                   ORDER BY wpm DESC, created_at ASC LIMIT 1""",
                (player_id, duration, difficulty),
            ).fetchone()
        try:
            return [float(v) for v in json.loads(row["wpm_series"])] if row else []
        except (ValueError, TypeError):
            return []

    def leaderboard(
        self,
        duration: Optional[int] = None,
        difficulty: Optional[str] = None,
        limit: int = config.LEADERBOARD_SIZE,
    ) -> pd.DataFrame:
        """Each player's single best result, ranked by WPM."""
        where = f"{COMPETITIVE} AND (:dur IS NULL OR r.duration_sec = :dur) AND (:diff IS NULL OR r.difficulty = :diff)"
        with self.connect() as conn:
            rows = conn.execute(
                _RANKED_SQL.format(where=where.replace("mode IN", "r.mode IN")),
                {"dur": duration, "diff": difficulty, "limit": int(limit)},
            ).fetchall()
        return _frame(rows, LEADERBOARD_COLUMNS)

    def daily_leaderboard(self, day: str, limit: int = config.LEADERBOARD_SIZE) -> pd.DataFrame:
        """Each player's best Daily Challenge result for ``day`` (ISO date)."""
        with self.connect() as conn:
            rows = conn.execute(
                _RANKED_SQL.format(where="r.mode = 'daily' AND r.challenge_date = :day"),
                {"day": day, "limit": int(limit)},
            ).fetchall()
        return _frame(rows, LEADERBOARD_COLUMNS)

    def daily_best(self, player_id: int, day: str) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                """SELECT wpm, accuracy FROM results
                   WHERE player_id = ? AND mode = 'daily' AND challenge_date = ?
                   ORDER BY wpm DESC, accuracy DESC LIMIT 1""",
                (player_id, day),
            ).fetchone()
        return dict(row) if row else None

    def key_stats(self, player_id: int, last_n: int = 300) -> dict[str, list[int]]:
        """Per-key ``[attempts, errors]`` summed over the player's most recent tests."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT mistakes_json FROM results WHERE player_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
                (player_id, last_n),
            ).fetchall()
        total: dict[str, list[int]] = {}
        for row in rows:
            try:
                data = json.loads(row["mistakes_json"])
            except (ValueError, TypeError):
                continue
            for key, pair in data.items():
                acc = total.setdefault(key, [0, 0])
                acc[0] += int(pair[0])
                acc[1] += int(pair[1])
        return total

    def platform_stats(self, today: Optional[str] = None) -> dict[str, Any]:
        """Community-wide numbers for the home page."""
        today = today or datetime.now().date().isoformat()
        with self.connect() as conn:
            totals = conn.execute(
                f"SELECT COUNT(*) AS tests, COUNT(DISTINCT player_id) AS players FROM results"
            ).fetchone()
            top = conn.execute(
                f"""SELECT p.name AS player, r.wpm FROM results r JOIN players p ON p.id = r.player_id
                    WHERE r.{COMPETITIVE} ORDER BY r.wpm DESC, r.accuracy DESC LIMIT 1"""
            ).fetchone()
            daily = conn.execute(
                "SELECT COUNT(DISTINCT player_id) AS n FROM results WHERE mode = 'daily' AND challenge_date = ?",
                (today,),
            ).fetchone()
        return {
            "tests": totals["tests"], "players": totals["players"],
            "top_player": top["player"] if top else None, "top_wpm": top["wpm"] if top else 0.0,
            "daily_players": daily["n"],
        }

    def delete_history(self, player_id: int) -> int:
        """Delete every result of one player. Returns the number of rows removed."""
        with self.connect() as conn:
            return conn.execute("DELETE FROM results WHERE player_id = ?", (player_id,)).rowcount
