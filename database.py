import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "shy_potatoes.db"

# 강원도 관광지 시드 (추후 한국관광공사 API로 동기화 예정)
SEED_SPOTS: list[dict[str, Any]] = [
    {"name": "방태산 자연휴양림 숲길", "region": "인제군", "description": "울창한 숲길 산책·힐링", "lat": 37.9188, "lng": 128.3506, "theme": "힐링"},
    {"name": "만항재 은하수 전망지", "region": "정선군", "description": "밤하늘 별·드라이브 명소", "lat": 37.2049, "lng": 128.9162, "theme": "야경"},
    {"name": "삼척 덕풍계곡 비경길", "region": "삼척시", "description": "계곡 트레킹·물소리 산책", "lat": 37.1126, "lng": 129.0452, "theme": "트레킹"},
    {"name": "영월 청령포 고요 산책", "region": "영월군", "description": "강변·역사 산책", "lat": 37.1822, "lng": 128.4616, "theme": "역사"},
    {"name": "평창 백룡동굴 탐방", "region": "평창군", "description": "동굴 탐방 체험", "lat": 37.3833, "lng": 128.4055, "theme": "체험"},
    {"name": "양구 파로호 둘레길", "region": "양구군", "description": "호수 둘레 자전거·산책", "lat": 38.1118, "lng": 127.9898, "theme": "자전거"},
    {"name": "속초 설악산 국립공원", "region": "속초시", "description": "케이블카·단풍·트레킹", "lat": 38.1702, "lng": 128.4913, "theme": "트레킹"},
    {"name": "강릉 경포대·해변", "region": "강릉시", "description": "호수·해변 산책", "lat": 37.8058, "lng": 128.8962, "theme": "힐링"},
    {"name": "강릉 안목해변 커피거리", "region": "강릉시", "description": "카페·일몰 드라이브", "lat": 37.7700, "lng": 128.9340, "theme": "힐링"},
    {"name": "춘천 남이섬", "region": "춘천시", "description": "섬 산책·자전거·드라마거리", "lat": 37.7906, "lng": 128.4661, "theme": "체험"},
    {"name": "춘천 소양강 스카이워크", "region": "춘천시", "description": "강 전망·포토스팟", "lat": 37.8762, "lng": 127.7298, "theme": "야경"},
    {"name": "원주 치악산 케이블카", "region": "원주시", "description": "산악 전망·단풍", "lat": 37.3800, "lng": 128.0540, "theme": "트레킹"},
    {"name": "홍천 비내섭계곡", "region": "홍천군", "description": "계곡 피서·물놀이", "lat": 37.6960, "lng": 127.6850, "theme": "힐링"},
    {"name": "태백산 천제단", "region": "태백시", "description": "고산 일출·눈꽃", "lat": 37.0953, "lng": 129.0302, "theme": "트레킹"},
    {"name": "정선 레일바이크", "region": "정선군", "description": "레일바이크·산골 풍경", "lat": 37.2200, "lng": 128.8400, "theme": "체험"},
    {"name": "정선 하이원 리조트 전망", "region": "정선군", "description": "산악 리조트·드라이브", "lat": 37.1830, "lng": 128.8180, "theme": "힐링"},
    {"name": "동해 무릉계곡", "region": "동해시", "description": "계곡·폭포 산책", "lat": 37.0750, "lng": 129.1400, "theme": "트레킹"},
    {"name": "동해 Mureung 건강숲", "region": "동해시", "description": "숲길 트레킹", "lat": 37.0900, "lng": 129.1200, "theme": "트레킹"},
    {"name": "삼척 케이블카·용화해수욕장", "region": "삼척시", "description": "해안 케이블카·해변", "lat": 37.0050, "lng": 129.1700, "theme": "체험"},
    {"name": "고성 통일전망대", "region": "고성군", "description": "전망·역사", "lat": 38.5050, "lng": 128.4100, "theme": "역사"},
    {"name": "양양 서피비치", "region": "양양군", "description": "서핑·해변", "lat": 38.0720, "lng": 128.6690, "theme": "체험"},
    {"name": "인제 원대리 자작나무숲", "region": "인제군", "description": "숲길 포토·힐링", "lat": 38.1550, "lng": 128.2100, "theme": "힐링"},
    {"name": "횡성 한우·둔내 온천", "region": "횡성군", "description": "먹거리·온천", "lat": 37.4900, "lng": 127.9900, "theme": "체험"},
    {"name": "화천 산천어축제 거리", "region": "화천군", "description": "겨울 축제·얼음낚시", "lat": 38.1060, "lng": 127.7080, "theme": "체험"},
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
