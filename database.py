import sqlite3
from pathlib import Path
from typing import Any

from content_loader import load_spots

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "shy_potatoes.db"

# Canonical owner: data/spots.json (via content_loader)
SEED_SPOTS: list[dict[str, Any]] = load_spots()


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
    with get_connection() as conn:
        for spot in SEED_SPOTS:
            conn.execute(
                """
                INSERT OR IGNORE INTO spots (name, region, description, lat, lng, theme)
                VALUES (:name, :region, :description, :lat, :lng, :theme);
                """,
                spot,
            )
        conn.commit()


def get_all_spots() -> list[dict[str, Any]]:
    """강원도 전체 관광지 — AI 큐레이션용 (필터 미적용)."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM spots ORDER BY region, name").fetchall()
    return [dict(row) for row in rows]


def get_filter_options() -> tuple[list[str], list[str]]:
    with get_connection() as conn:
        regions = [row["region"] for row in conn.execute("SELECT DISTINCT region FROM spots ORDER BY region")]
        themes = [row["theme"] for row in conn.execute("SELECT DISTINCT theme FROM spots ORDER BY theme")]
    return regions, themes


def get_spots(region: str | None = None, theme: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM spots WHERE 1=1"
    params: list[Any] = []

    if region and region != "전체":
        query += " AND region = ?"
        params.append(region)
    if theme and theme != "전체":
        query += " AND theme = ?"
        params.append(theme)

    query += " ORDER BY region, name"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_spots_by_names(names: list[str]) -> list[dict[str, Any]]:
    if not names:
        return []
    all_spots = get_all_spots()
    order = {n: i for i, n in enumerate(names)}
    matched = [s for s in all_spots if s["name"] in names]
    matched.sort(key=lambda s: order.get(s["name"], 999))
    return matched
