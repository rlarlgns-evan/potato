"""
강원도 홈 화면 콘텐츠 (추후 한국관광공사 API 연동 예정).
날씨: Open-Meteo · 인구순 도시 로테이션.
"""

import json
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from content_loader import load_catalog, load_festivals, load_region_intro_md

_catalog = load_catalog()
GANGWON_CITIES: list[dict[str, Any]] = _catalog["cities"]
WEATHER_ICONS: dict[str, dict[str, str]] = {
    k: {"icon": v["icon"], "label": v["label"], "thumb_bg": v["thumb_bg"]}
    for k, v in _catalog["weather_icons"].items()
}
FESTIVAL_ICONS = _catalog["festival_icons"]


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
    ordered = sorted(GANGWON_CITIES, key=lambda x: x.get("pop_rank", 99))
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
    return load_festivals()


def get_region_intro() -> str:
    return load_region_intro_md()
