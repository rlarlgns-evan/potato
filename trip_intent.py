"""Trip intent detection — complex prompts must use AI, not local keyword match."""

from __future__ import annotations

import re
from typing import Any

from content_loader import load_catalog

_COMPLEX_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"1박\s*2일|2박\s*3일|3박\s*4일|당일치기|무박|숙박|\d+박",
        r"대중교통|KTX|기차|버스|열차|지하철|SRT|ITX|무궁화|고속버스",
        r"에서\s*출발|출발|\w+시\b|\w+구\b|경기|서울|인천|부산|대전|광주",
        r"여자친구|남자친구|커플|아이와|가족|친구와|연인|부모님|애인",
        r"숙소|호텔|펜션|게스트하우스|리조트|민박|잠을|숙박",
        r"최적\s*경로|길찾|이동\s*경로|동선",
    )
]

_THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "바다": ("바다", "해변", "해수욕", "서핑", "일몰", "해변가"),
    "산": ("산", "트레킹", "설악", "치악", "등산", "단풍"),
    "온천": ("온천", "스파"),
    "커피": ("커피", "카페"),
    "드라이브": ("드라이브", "전망", "야경", "드라이브"),
    "로맨틱": ("여자친구", "남자친구", "커플", "연인", "데이트", "로맨틱"),
}


def needs_ai_curation(message: str) -> bool:
    """출발·교통·숙박·기간 등 복합 조건이 있으면 반드시 AI 호출."""
    msg = message.strip()
    if not msg:
        return False
    return any(p.search(msg) for p in _COMPLEX_PATTERNS)


def detect_themes(message: str) -> list[str]:
    themes: list[str] = []
    for theme, kws in _THEME_KEYWORDS.items():
        if any(kw in message for kw in kws):
            themes.append(theme)
    return themes


def detect_origin(message: str) -> str:
    catalog = load_catalog()
    origins: dict[str, Any] = catalog.get("transit_origins") or {}
    for name in sorted(origins.keys(), key=len, reverse=True):
        short = name.replace("시", "").replace("군", "").replace("구", "")
        if name in message or (len(short) >= 2 and short in message):
            return name
    match = re.search(r"(\S+(?:시|구|군))(?:\s*에서|\s*출발)?", message)
    if match:
        return match.group(1)
    return ""


def _format_origin_routes(city: str, data: dict[str, Any]) -> str:
    hub = data.get("hub", "")
    lines = [f"{city} (집결 hub: {hub})"]
    for route in data.get("routes") or []:
        lines.append(
            f"  → {route.get('dest', '')} | {route.get('mode', '')} | "
            f"{route.get('via', '')} | {route.get('note', '')}"
        )
    return "\n".join(lines)


def transit_reference_block(origin: str = "") -> str:
    catalog = load_catalog()
    origins: dict[str, Any] = catalog.get("transit_origins") or {}
    if not origins:
        return ""
    if origin and origin in origins:
        return _format_origin_routes(origin, origins[origin])
    lines = ["주요 출발지 → 강원 대중교통 참고:"]
    for city, data in list(origins.items())[:5]:
        lines.append(_format_origin_routes(city, data))
    return "\n".join(lines)


def build_trip_hints(message: str) -> str:
    origin = detect_origin(message)
    themes = detect_themes(message)
    lines = ["Parse user request into trip_intent JSON fields."]
    if origin:
        lines.append(f"Detected origin hint: {origin}")
    if themes:
        lines.append(f"Detected theme hints: {', '.join(themes)}")
    ref = transit_reference_block(origin)
    if ref:
        lines.append(ref)
    return "\n".join(lines)


def resolve_origin_entry(origin_text: str) -> tuple[str, dict[str, Any]] | None:
    text = (origin_text or "").strip()
    if not text:
        return None
    catalog = load_catalog()
    origins: dict[str, Any] = catalog.get("transit_origins") or {}
    if text in origins:
        return text, origins[text]
    for name in sorted(origins.keys(), key=len, reverse=True):
        short = name.replace("시", "").replace("군", "").replace("구", "")
        if name in text or (len(short) >= 2 and short in text):
            return name, origins[name]
    return None


def pick_origin_coords(data: dict[str, Any], transport: str = "") -> tuple[float, float] | None:
    transport_text = (transport or "").lower()
    if data.get("hub_lat") is not None and re.search(
        r"ktx|기차|itx|srt|열차|지하철|버스|대중교통", transport_text
    ):
        return float(data["hub_lat"]), float(data["hub_lng"])
    if data.get("lat") is not None and data.get("lng") is not None:
        return float(data["lat"]), float(data["lng"])
    return None


def build_origin_route_step(
    label: str,
    data: dict[str, Any],
    transport: str = "",
    outbound: str = "",
) -> dict[str, Any] | None:
    coords = pick_origin_coords(data, transport)
    if not coords:
        return None
    lat, lng = coords
    hub = data.get("hub") or ""
    return {
        "order": 1,
        "kind": "origin",
        "day": 0,
        "spot_name": f"출발 · {label}",
        "region": label,
        "theme": "출발",
        "lat": lat,
        "lng": lng,
        "stay_minutes": 0,
        "why": f"출발 · {hub}" if hub else f"출발 · {label}",
        "move_to_next": (outbound or "").strip(),
    }


def attach_origin_step(
    steps: list[dict[str, Any]],
    trip_intent: dict[str, Any] | None,
    transit_plan: dict[str, Any] | None,
    user_message: str = "",
) -> list[dict[str, Any]]:
    intent = trip_intent or {}
    transit = transit_plan or {}
    origin_text = intent.get("origin") or detect_origin(user_message)
    hit = resolve_origin_entry(str(origin_text or ""))
    if not hit:
        return steps
    label, data = hit
    origin = build_origin_route_step(
        label,
        data,
        str(intent.get("transport") or ""),
        str(transit.get("outbound") or ""),
    )
    if not origin:
        return steps
    renumbered = [{**step, "order": idx + 2} for idx, step in enumerate(steps)]
    return [origin, *renumbered]
