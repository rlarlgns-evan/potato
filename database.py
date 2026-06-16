import sqlite3
from pathlib import Path
from typing import Any

from content_loader import load_spots

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "shy_potatoes.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS spots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                region TEXT NOT NULL,
                description TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                theme TEXT NOT NULL
            );
            """
        )
        conn.commit()
    seed_data()


def seed_data() -> None:
    load_spots.cache_clear()
    spots = load_spots()
    with get_connection() as conn:
        for spot in spots:
            conn.execute(
                """
                INSERT INTO spots (name, region, description, lat, lng, theme)
                VALUES (:name, :region, :description, :lat, :lng, :theme)
                ON CONFLICT(name) DO UPDATE SET
                    region = excluded.region,
                    description = excluded.description,
                    lat = excluded.lat,
                    lng = excluded.lng,
                    theme = excluded.theme;
                """,
                spot,
            )
        conn.commit()


def get_all_spots() -> list[dict[str, Any]]:
    """강원도 전체 관광지 — AI 큐레이션용 (필터 미적용)."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM spots ORDER BY region, name").fetchall()
    return [dict(row) for row in rows]
