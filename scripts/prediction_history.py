"""SQLite-backed history of dashboard audio predictions (no audio bytes stored)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path.home() / ".maemi_translater" / "prediction_history.sqlite3"


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS prediction_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    source_type TEXT NOT NULL CHECK (source_type IN ('upload', 'library')),
    audio_name TEXT NOT NULL,
    predicted_species TEXT,
    confidence REAL,
    decision_status TEXT NOT NULL,
    duration_sec REAL,
    source_model TEXT
)
"""


def initialize_database(db_path: Path = DEFAULT_DB_PATH) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.execute(CREATE_TABLE)


def save_prediction(
    result: dict[str, Any],
    *,
    source_type: str,
    audio_name: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """Persist a successful inference and return the generated history ID."""
    if source_type not in ("upload", "library"):
        raise ValueError("source_type must be 'upload' or 'library'")

    initialize_database(db_path)
    ranking = result.get("aggregate_ranking") or []
    top = ranking[0] if ranking else {}
    final = result.get("final_recommendation") or result.get("recommendation") or {}
    with sqlite3.connect(db_path, timeout=10) as conn:
        cursor = conn.execute(
            """
            INSERT INTO prediction_history
                (source_type, audio_name, predicted_species, confidence,
                 decision_status, duration_sec, source_model)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_type,
                Path(audio_name).name,
                top.get("label"),
                top.get("mean_probability"),
                final.get("status", "unknown"),
                result.get("duration_sec"),
                final.get("source_model"),
            ),
        )
        return int(cursor.lastrowid)


def list_predictions(db_path: Path = DEFAULT_DB_PATH, *, limit: int = 20) -> list[dict[str, Any]]:
    """Return newest predictions first; the API caps its limit at 100."""
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    initialize_database(db_path)
    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, created_at, source_type, audio_name, predicted_species,
                   confidence, decision_status, duration_sec, source_model
            FROM prediction_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
