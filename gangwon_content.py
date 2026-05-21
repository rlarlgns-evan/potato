"""
강원도 홈 화면 콘텐츠 (추후 한국관광공사 API 연동 예정).
날씨: Open-Meteo · 인구순 도시 로테이션.
"""

import json
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

# 인구순 (시·군 기준 대략적 순위, 2023~2024 통계 참고)
GANGWON_CITIES: list[dict[str, Any]] = [
    {"city": "원주", "lat": 37.3422, "lng": 127.9202, "pop_rank": 1},
    {"city": "춘천", "lat": 37.8747, "lng": 127.7342, "pop_rank": 2},
    {"city": "강릉", "lat": 37.7519, "lng": 129.2022, "pop_rank": 3},
    {"city": "동해", "lat": 37.5247, "lng": 129.1144, "pop_rank": 4},
    {"city": "속초", "lat": 38.2070, "lng": 128.5918, "pop_rank": 5},
    {"city": "삼척", "lat": 37.4498, "lng": 129.1652, "pop_rank": 6},
    {"city": "홍천", "lat": 37.6970, "lng": 127.8887, "pop_rank": 7},
    {"city": "태백", "lat": 37.1641, "lng": 128.9856, "pop_rank": 8},
    {"city": "정선", "lat": 37.3807, "lng": 128.6608, "pop_rank": 9},
    {"city": "평창", "lat": 37.3705, "lng": 128.3900, "pop_rank": 10},
]

WEATHER_ICONS: dict[str, dict[str, str]] = {
    "sunny": {"icon": "☀", "label": "맑음", "thumb_bg": "linear-gradient(135deg,#FDE68A,#FBBF24)"},
    "partly_cloudy": {"icon": "◐", "label": "구름 조금", "thumb_bg": "linear-gradient(135deg,#BAE6FD,#7DD3FC)"},
    "cloudy": {"icon": "☁", "label": "흐림", "thumb_bg": "linear-gradient(135deg,#E2E8F0,#94A3B8)"},
    "fog": {"icon": "≡", "label": "안개", "thumb_bg": "linear-gradient(135deg,#CBD5E1,#94A3B8)"},
    "rain": {"icon": "☂", "label": "비", "thumb_bg": "linear-gradient(135deg,#93C5FD,#3B82F6)"},
    "snow": {"icon": "❄", "label": "눈", "thumb_bg": "linear-gradient(135deg,#E0F2FE,#BAE6FD)"},
    "thunder": {"icon": "⚡", "label": "뇌우", "thumb_bg": "linear-gradient(135deg,#C4B5FD,#7C3AED)"},
}

FESTIVAL_ICONS = ["🎪", "🎭", "🎶", "🐟", "☕", "🎿", "🌸", "🍁"]


def wmo_to_condition(code: int) -> str:
    if code == 0:
        return "sunny"
    if code in (1, 2):
        return "partly_cloudy"
    if code == 3:
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "thunder"
    return "cloudy"


def build_weather_tip(temp: int, cond: str, temp_max: float | None, temp_min: float | None) -> str:
    tips: list[str] = []
    if temp_max is not None and temp_min is not None:
        diff = round(temp_max - temp_min)
        if diff >= 8:
            tips.append(f"일교차 {diff}°C · 겉옷을 챙기세요")
        elif diff >= 5:
            tips.append("일교차 있음 · 가벼운 겉옷 추천")
    if temp <= 3:
        tips.append("체감이 춥습니다 · 따뜻하게 입으세요")
    elif temp >= 28:
        tips.append("더워요 · 수분·자외선 차단")
    if cond == "rain":
        tips.append("우산을 챙기세요")
    elif cond == "snow":
        tips.append("미끄럼 주의 · 방한 필수")
    elif cond == "fog":
        tips.append("시야가 짧을 수 있어요 · 운전 주의")
    elif cond == "thunder":
        tips.append("번개 가능 · 실외 활동 주의")
    elif cond in ("sunny", "partly_cloudy") and 8 <= temp <= 22:
        tips.append("산책·드라이브 좋은 날씨")
    if not tips:
        tips.append("외출 전 현지 날씨를 확인하세요")
    return " · ".join(tips[:2])


def _fetch_city_weather(city: str, lat: float, lng: float) -> dict[str, Any]:
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lng}"
        "&current=temperature_2m,weather_code"
        "&daily=temperature_2m_max,temperature_2m_min"
        "&timezone=Asia%2FSeoul&forecast_days=1"
    )
    with urlopen(url, timeout=6) as resp:
        data = json.loads(resp.read().decode())
    current = data.get("current", {})
    daily = data.get("daily", {})
    temp = current.get("temperature_2m", 0)
    code = int(current.get("weather_code", 3))
    tmax = (daily.get("temperature_2m_max") or [None])[0]
    tmin = (daily.get("temperature_2m_min") or [None])[0]
    cond = wmo_to_condition(code)
    meta = WEATHER_ICONS[cond]
    temp_int = round(temp)
    return {
        "city": city,
        "temp": temp_int,
        "temp_display": f"{temp_int}°C",
        "temp_range": f"{round(tmin)}° ~ {round(tmax)}°" if tmin is not None and tmax is not None else "",
        "condition": cond,
        "icon": meta["icon"],
        "thumb_bg": meta["thumb_bg"],
        "label": meta["label"],
        "tip": build_weather_tip(temp_int, cond, tmax, tmin),
    }


def _placeholder_cities() -> list[dict[str, Any]]:
    samples = [
        ("원주", "partly_cloudy", 11, 18, 4),
        ("춘천", "sunny", 12, 19, 5),
        ("강릉", "cloudy", 10, 14, 7),
        ("동해", "rain", 9, 12, 6),
        ("속초", "partly_cloudy", 8, 11, 3),
        ("삼척", "sunny", 11, 15, 8),
        ("홍천", "cloudy", 10, 16, 6),
        ("태백", "snow", 2, 5, -3),
        ("정선", "cloudy", 7, 12, 4),
        ("평창", "snow", 3, 7, -2),
    ]
    out = []
    for city, cond, temp, hi, lo in samples:
        meta = WEATHER_ICONS[cond]
        out.append(
            {
                "city": city,
                "temp": temp,
                "temp_display": f"{temp}°C",
                "temp_range": f"{lo}° ~ {hi}°",
                "condition": cond,
                "icon": meta["icon"],
                "thumb_bg": meta["thumb_bg"],
                "label": meta["label"],
                "tip": build_weather_tip(temp, cond, hi, lo),
            }
        )
    return out


def get_weather_cities() -> list[dict[str, Any]]:
    """인구순 정렬된 강원 도시 날씨."""
    ordered = sorted(GANGWON_CITIES, key=lambda x: x["pop_rank"])
    results: list[dict[str, Any]] = []
    for c in ordered:
        try:
            results.append(_fetch_city_weather(c["city"], c["lat"], c["lng"]))
        except (URLError, OSError, json.JSONDecodeError, KeyError, ValueError, TypeError):
            continue
    return results if results else _placeholder_cities()


def get_weather() -> dict[str, str]:
    cities = get_weather_cities()
    first = cities[0]
    return {
        "region": f"{first['city']} 기준",
        "temp": first["temp_display"],
        "condition": f"{first['label']}",
        "tip": first.get("tip", ""),
    }


def get_festivals() -> list[dict[str, str]]:
    return [
        {"title": "평창 송어축제", "period": "1~2월", "place": "평창군", "desc": "얼음낚시·지역 먹거리"},
        {"title": "화천 산천어축제", "period": "1월", "place": "화천군", "desc": "빙어·얼음낚시"},
        {"title": "강릉 커피축제", "period": "10월", "place": "강릉시", "desc": "안목·경포 카페거리"},
        {"title": "정선 아리랑제", "period": "10월", "place": "정선군", "desc": "전통공연·레일바이크"},
        {"title": "춘천 막국수 닭갈비 축제", "period": "10월", "place": "춘천시", "desc": "로컬 먹거리"},
        {"title": "속초 설악산 단풍제", "period": "10월", "place": "속초시", "desc": "단풍·트레킹"},
        {"title": "삼척 비치 페스티벌", "period": "7~8월", "place": "삼척시", "desc": "해변·공연"},
        {"title": "원주 댄싱카니발", "period": "9월", "place": "원주시", "desc": "거리공연·문화"},
    ]


def get_highlights() -> list[dict[str, Any]]:
    return [
        {"title": "설악산 단풍", "region": "속초·고성", "icon": "▲", "thumb_bg": "linear-gradient(135deg,#0D9488,#14B8A6)"},
        {"title": "남이섬·소나무", "region": "춘천", "icon": "♣", "thumb_bg": "linear-gradient(135deg,#0891B2,#22D3EE)"},
        {"title": "동해 해변 드라이브", "region": "동해·삼척", "icon": "≈", "thumb_bg": "linear-gradient(135deg,#0284C7,#38BDF8)"},
    ]


def get_region_intro() -> str:
    return (
        "강원도는 산·바다·계곡이 가까워 **당일·반나절 여행**에 잘 맞아요. "
        "AI가 전역 관광지 중에서 취향에 맞는 동선을 골라 드립니다."
    )
