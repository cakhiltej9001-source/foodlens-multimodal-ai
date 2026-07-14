from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def init_db(db_path: str) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                image_name TEXT NOT NULL,
                dish_name TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                nutrition_json TEXT NOT NULL,
                recipes_json TEXT NOT NULL
            )
            """
        )
        connection.commit()


def save_analysis(
    db_path: str,
    image_name: str,
    analysis: dict[str, Any],
    nutrition: list[dict[str, Any]],
    recipes: dict[str, Any],
) -> None:
    init_db(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO analyses (
                created_at, image_name, dish_name, analysis_json, nutrition_json, recipes_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                image_name,
                analysis.get("dish_name", "Unknown dish"),
                json.dumps(analysis, ensure_ascii=False),
                json.dumps(nutrition, ensure_ascii=False),
                json.dumps(recipes, ensure_ascii=False),
            ),
        )
        connection.commit()


def list_recent_analyses(db_path: str, limit: int = 10) -> list[dict[str, Any]]:
    init_db(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT created_at, image_name, dish_name
            FROM analyses
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
