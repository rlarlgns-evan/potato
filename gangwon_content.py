"""
강원도 홈 화면 콘텐츠 (추후 한국관광공사 API 연동 예정).
날씨: Open-Meteo 무료 API (키 불필요) · 실패 시 플레이스홀더.
"""

import json
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

# 강원 주요 도시 (lat, lon)
GANGWON_CITIES: list[dict[str, Any]] = [
    {"city": "춘천", "lat": 37.8747, "lng": 127.7342},
    {"city": "원주", "lat": 37.3422, "lng": 127.9202},
    {"city": "강릉", "lat": 37.7519, "lng": 129.2022},
    {"city": "삼척", "lat": 37.4498, "lng": 129.1652},
    {"city": "속초", "lat": 38.2070, "lng": 128.5918},
    {"city": "동해", "lat": 37.5247, "lng": 129.1144},
    {"city": "평창", "lat": 37.3705, "lng": 128.3900},
    {"city": "정선", "lat": 37.3807, "lng": 128.6608},
]

WEATHER_ICONS: dict[str, dict[str, str]] = {
    "sunny": {"icon": "☀️", "label": "맑음", "bg": "#FEF9C3"},
    "partly_cloudy": {"icon": "⛅", "label": "구름 조금", "bg": "#E0F2FE"},
    "cloudy": {"icon": "☁️", "label": "흐림", "bg": "#F1F5F9"},
    "fog": {"icon": "🌫️", "label": "안개", "bg": "#E2E8F0"},
    "rain": {"icon": "🌧️", "label": "비", "bg": "#DBEAFE"},
    "snow": {"icon": "❄️", "label": "눈", "bg": "#F0F9FF"},
    "thunder": {"icon": "⛈️", "label": "뇌우", "bg": "#EDE9FE"},
}


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


def _placeholder_cities() -> list[dict[str, Any]]:
    samples = [
        ("춘천", "sunny", 12),
        ("원주", "partly_cloudy", 11),
        ("강릉", "cloudy", 10),
        ("삼척", "rain", 9),
        ("속초", "partly_cloudy", 8),
        ("동해", "sunny", 11),
        ("평창", "snow", 4),
        ("정선", "cloudy", 7),
    ]
    out = []
    for city, cond, temp in samples:
        meta = WEATHER_ICONS[cond]
        out.append(
            {
                "city": city,
                "temp": temp,
                "temp_display": f"{temp}°C",
                "condition": cond,
                "icon": meta["icon"],
                "label": meta["label"],
                "bg": meta["bg"],
                "tip": "실시간 연동 전 샘플 데이터",
            }
        )
    return out


def _fetch_city_weather(city: str, lat: float, lng: float) -> dict[str, Any]:
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lng}"
        "&current=temperature_2m,weather_code"
        "&timezone=Asia%2FSeoul"
    )
    with urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read().decode())
    current = data.get("current", {})
    temp = current.get("temperature_2m", 0)
    code = int(current.get("weather_code", 3))
    cond = wmo_to_condition(code)
    meta = WEATHER_ICONS[cond]
    temp_int = round(temp)
    return {
        "city": city,
        "temp": temp_int,
        "temp_display": f"{temp_int}°C",
        "condition": cond,
        "icon": meta["icon"],
        "label": meta["label"],
        "bg": meta["bg"],
        "tip": f"{city} 현재 체감 · 외출 전 확인",
    }


def get_weather_cities() -> list[dict[str, Any]]:
    """강원 주요 도시 날씨 목록 (Open-Meteo, 도시별)."""
    results: list[dict[str, Any]] = []
    for c in GANGWON_CITIES:
        try:
            results.append(_fetch_city_weather(c["city"], c["lat"], c["lng"]))
        except (URLError, OSError, json.JSONDecodeError, KeyError, ValueError):
            continue
    return results if results else _placeholder_cities()


def get_weather() -> dict[str, str]:
    """하위 호환 — 첫 도시 요약."""
    cities = get_weather_cities()
    first = cities[0]
    return {
        "region": f"{first['city']} 기준",
        "temp": first["temp_display"],
        "condition": f"{first['icon']} {first['label']}",
        "tip": first.get("tip", ""),
    }


def get_festivals() -> list[dict[str, str]]:
    return [
        {"title": "평창 송어축제", "period": "겨울 시즌", "place": "평창군", "desc": "얼음낚시·지역 먹거리"},
        {"title": "강릉 커피축제", "period": "10월", "place": "강릉시", "desc": "안목·경포 카페 거리"},
        {"title": "정선 아리랑제", "period": "10월", "place": "정선군", "desc": "전통 공연·레일바이크"},
    ]


def get_highlights() -> list[dict[str, Any]]:
    return [
        {"title": "설악산 단풍", "region": "속초·고성", "emoji": "🏔️", "gradient": "linear-gradient(135deg,#0D9488,#14B8A6)"},
        {"title": "남이섬·소나무", "region": "춘천", "emoji": "🌲", "gradient": "linear-gradient(135deg,#0891B2,#22D3EE)"},
        {"title": "동해 해변 드라이브", "region": "동해·삼척", "emoji": "🌊", "gradient": "linear-gradient(135deg,#0284C7,#38BDF8)"},
    ]


def get_region_intro() -> str:
    return (
        "강원도는 산·바다·계곡이 가까워 **당일·반나절 여행**에 잘 맞아요. "
        "AI가 전역 관광지 중에서 취향에 맞는 동선을 골라 드립니다."
    )
