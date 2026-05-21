"""카카오 지도 — Streamlit 커스텀 컴포넌트 (앱과 동일 도메인에서 SDK 로드)."""

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from config import get_env

_COMPONENT_DIR = Path(__file__).resolve().parent / "kakao_map_component"
_kakao_map_component = components.declare_component(
    "kakao_map",
    path=str(_COMPONENT_DIR),
)

_DOMAIN_HINT = (
    "Kakao Developers → JavaScript 키 → **JavaScript SDK 도메인**에 아래를 **공백 없이** 등록:\n"
    "- `https://kangwon-potato.streamlit.app`\n"
    "- `http://localhost:8501` (로컬)\n"
    "카카오 **로그인 Redirect URI**는 지도용이 아니므로 비워도 됩니다."
)


def get_kakao_app_key() -> str:
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
    key = get_env("KAKAO_MAP_APP_KEY")
    if key:
        return key
    try:
        key = str(st.secrets["KAKAO_MAP_APP_KEY"]).strip()
        if key:
            return key
    except Exception:
        pass
    try:
        key = str(st.secrets.get("KAKAO_MAP_APP_KEY", "")).strip()
        if key:
            return key
    except Exception:
        pass
    return ""


def build_route_markers(
    curated: list[dict[str, Any]],
    steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """동선 순서 + AI 설명을 지도 마커 데이터에 합칩니다."""
    by_name = {s["name"]: s for s in curated}
    markers: list[dict[str, Any]] = []
    for step in steps:
        spot = by_name.get(step.get("spot_name", ""))
        if not spot:
            continue
        markers.append(
            {
                "name": spot["name"],
                "lat": float(spot["lat"]),
                "lng": float(spot["lng"]),
                "region": spot.get("region", step.get("region", "")),
                "theme": spot.get("theme", step.get("theme", "")),
                "description": (spot.get("description") or "")[:220],
                "why": (step.get("why") or spot.get("description") or "")[:280],
                "stay_minutes": step.get("stay_minutes"),
                "move_to_next": (step.get("move_to_next") or "")[:120],
                "order": int(step.get("order", len(markers) + 1)),
            }
        )
    if not markers:
        for idx, s in enumerate(curated, start=1):
            markers.append(
                {
                    "name": s["name"],
                    "lat": float(s["lat"]),
                    "lng": float(s["lng"]),
                    "region": s.get("region", ""),
                    "theme": s.get("theme", ""),
                    "description": (s.get("description") or "")[:220],
                    "why": "",
                    "stay_minutes": None,
                    "move_to_next": "",
                    "order": idx,
                }
            )
    return markers


def build_kakao_route_url(markers: list[dict[str, Any]]) -> str | None:
    """카카오맵 앱/웹에서 전체 동선 열기."""
    if not markers:
        return None
    if len(markers) == 1:
        m = markers[0]
        return f"https://map.kakao.com/link/map/{quote(m['name'])},{m['lat']},{m['lng']}"
    parts = [f"{quote(m['name'])},{m['lat']},{m['lng']}" for m in markers]
    return "https://map.kakao.com/link/by/car/" + "/".join(parts)


def render_kakao_map(
    spots: list[dict[str, Any]],
    center_lat: float,
    center_lng: float,
    app_key: str,
    height: int = 500,
    route_spots: list[dict[str, Any]] | None = None,
    show_route: bool = False,
    focus_order: int = 0,
    focus_label: str = "",
    title: str = "Live Kakao Map",
) -> None:
    display_spots = route_spots if route_spots else spots
    if not display_spots:
        display_spots = [
            {
                "name": "강원도",
                "lat": center_lat,
                "lng": center_lng,
                "region": "",
                "theme": "",
                "description": "",
                "why": "",
                "stay_minutes": None,
                "move_to_next": "",
                "order": 0,
            }
        ]

    markers = []
    for idx, s in enumerate(display_spots, start=1):
        markers.append(
            {
                "name": s["name"],
                "lat": float(s["lat"]),
                "lng": float(s["lng"]),
                "region": s.get("region", ""),
                "theme": s.get("theme", ""),
                "description": (s.get("description") or "")[:220],
                "why": (s.get("why") or s.get("description") or "")[:280],
                "stay_minutes": s.get("stay_minutes"),
                "move_to_next": (s.get("move_to_next") or "")[:120],
                "order": int(s.get("order", idx)),
            }
        )

    shell_h = height + 88
    _kakao_map_component(
        appkey=app_key or "",
        markers_json=json.dumps(markers, ensure_ascii=False),
        center_lat=float(center_lat),
        center_lng=float(center_lng),
        show_route=bool(show_route and len(display_spots) > 1),
        show_numbers=bool(route_spots),
        focus_order=int(focus_order or 0),
        focus_label=focus_label or "",
        title=title,
        height=int(height),
        key="trip_map",
        default=None,
    )

    if not app_key:
        st.info(
            "카카오 **JavaScript 키**가 없어 OpenStreetMap으로 표시됩니다. "
            "Secrets에 `KAKAO_MAP_APP_KEY`를 설정하세요."
        )
    else:
        with st.expander("지도가 OpenStreetMap으로만 보이나요?"):
            st.markdown(_DOMAIN_HINT)
