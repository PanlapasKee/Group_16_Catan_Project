"""
database.py
===========
Handles persistence for the Catan game:
  - JSON quick-save / quick-load  (saves full engine state)
  - SQLite history log            (stores finished game records)

All file paths are relative to the directory where main.py lives so
the project runs without modification on any machine.
"""

from __future__ import annotations
import json
import sqlite3
import os
from typing import List, Optional, Dict, Any

from data.models import GameRecord
from utils.constants import SAVE_FILE, DB_FILE


def _save_dir() -> str:
    """Return the project root directory (where main.py lives)."""
    # Walk up from this file to the root
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(here)


def _save_path() -> str:
    return os.path.join(_save_dir(), SAVE_FILE)


def _db_path() -> str:
    return os.path.join(_save_dir(), DB_FILE)


# ---------------------------------------------------------------------------
# JSON save / load
# ---------------------------------------------------------------------------

def save_game(engine_dict: Dict[str, Any]) -> bool:
    """
    Serialise the engine state dict to a JSON file.
    :return: True on success.
    """
    try:
        with open(_save_path(), "w", encoding="utf-8") as fh:
            json.dump(engine_dict, fh, indent=2)
        return True
    except OSError as exc:
        print(f"[database] Save failed: {exc}")
        return False


def load_game() -> Optional[Dict[str, Any]]:
    """
    Load a previously saved engine state dict.
    :return: dict on success, None if file missing or corrupt.
    """
    path = _save_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[database] Load failed: {exc}")
        return None


def delete_save() -> None:
    """Remove the current save file (e.g. after game ends)."""
    path = _save_path()
    if os.path.exists(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# SQLite history
# ---------------------------------------------------------------------------

def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the history table if it does not exist."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id    TEXT    NOT NULL,
                timestamp  TEXT    NOT NULL,
                winner     TEXT    NOT NULL,
                turn_count INTEGER NOT NULL,
                data_json  TEXT    NOT NULL
            )
        """)
        conn.commit()


def record_game(record: GameRecord) -> bool:
    """Insert a finished game record into SQLite."""
    try:
        init_db()
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO game_history
                    (game_id, timestamp, winner, turn_count, data_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record.game_id,
                    record.timestamp,
                    record.winner,
                    record.turn_count,
                    json.dumps(record.to_dict()),
                ),
            )
            conn.commit()
        return True
    except sqlite3.Error as exc:
        print(f"[database] DB insert failed: {exc}")
        return False


def fetch_history(limit: int = 20) -> List[GameRecord]:
    """Return the most recent finished games (newest first)."""
    try:
        init_db()
        with _get_connection() as conn:
            rows = conn.execute(
                "SELECT data_json FROM game_history "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        records = []
        for row in rows:
            try:
                d = json.loads(row["data_json"])
                records.append(GameRecord.from_dict(d))
            except Exception:
                pass
        return records
    except sqlite3.Error as exc:
        print(f"[database] DB fetch failed: {exc}")
        return []


def fetch_player_stats() -> List[Dict[str, Any]]:
    """Return win counts per player name across all recorded games."""
    try:
        init_db()
        with _get_connection() as conn:
            rows = conn.execute(
                "SELECT winner, COUNT(*) as wins "
                "FROM game_history GROUP BY winner ORDER BY wins DESC"
            ).fetchall()
        return [{"name": r["winner"], "wins": r["wins"]} for r in rows]
    except sqlite3.Error as exc:
        print(f"[database] Stats failed: {exc}")
        return []
