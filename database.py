import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "shy_potatoes.db"


SEED_SPOTS: list[dict[str, Any]] = [
    {
        "name": "방태산 자연휴양림 숲길",
        "region": "인제군",
        "description": "사람이 몰리지 않는 울창한 숲길 산책 코스",
        "lat": 37.9188,
        "lng": 128.3506,
        "theme": "힐링",
    },
    {
        "name": "만항재 은하수 전망지",
        "region": "정선군",
        "description": "여름 밤하늘 별 관측이 좋은 드라이브 명소",
        "lat": 37.2049,
        "lng": 128.9162,
        "theme": "야경",
    },
    {
        "name": "삼척 덕풍계곡 비경길",
        "region": "삼척시",
        "description": "한적하게 물소리를 들으며 걷기 좋은 계곡 코스",
        "lat": 37.1126,
        "lng": 129.0452,
        "theme": "트레킹",
    },
    {
        "name": "영월 청령포 고요 산책",
        "region": "영월군",
        "description": "역사와 강변 풍경을 동시에 즐기는 한적한 산책지",
        "lat": 37.1822,
        "lng": 128.4616,
        "theme": "역사",
    },
    {
        "name": "평창 백룡동굴 탐방길",
        "region": "평창군",
        "description": "사전 예약 후 탐방 가능한 이색 동굴 체험",
        "lat": 37.3833,
        "lng": 128.4055,
        "theme": "체험",
    },
    {
        "name": "양구 파로호 둘레길",
        "region": "양구군",
        "description": "호수 주변을 천천히 둘러보는 조용한 자전거 코스",
        "lat": 38.1118,
        "lng": 127.9898,
        "theme": "자전거",
    },
]


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
        count = conn.execute("SELECT COUNT(*) AS cnt FROM spots").fetchone()["cnt"]
        if count > 0:
            return

        conn.executemany(
            """
            INSERT INTO spots (name, region, description, lat, lng, theme)
            VALUES (:name, :region, :description, :lat, :lng, :theme);
            """,
            SEED_SPOTS,
        )
        conn.commit()


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
