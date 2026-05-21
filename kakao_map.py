"""카카오 지도 — Streamlit components.html (Cloud 호환)."""

import html as html_module
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from config import get_env

_COMPONENT_DIR = Path(__file__).resolve().parent / "kakao_map_component"
_MAP_JS = (_COMPONENT_DIR / "map_logic.js").read_text(encoding="utf-8")

_DOMAIN_HINT = (
    "Kakao Developers → JavaScript 키 → **JavaScript SDK 도메인** (공백 없이):\n"
    "- `https://kangwon-potato.streamlit.app`\n"
    "- `http://localhost:8501`"
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
    if not markers:
        return None
    if len(markers) == 1:
        m = markers[0]
        return f"https://map.kakao.com/link/map/{quote(m['name'])},{m['lat']},{m['lng']}"
    parts = [f"{quote(m['name'])},{m['lat']},{m['lng']}" for m in markers]
    return "https://map.kakao.com/link/by/car/" + "/".join(parts)


def _build_map_html(
    app_key: str,
    markers: list[dict[str, Any]],
    center_lat: float,
    center_lng: float,
    show_route: bool,
    show_numbers: bool,
    focus_order: int,
    focus_label: str,
    title: str,
    height: int,
) -> str:
    cfg = {
        "appkey": app_key or "",
        "markers": markers,
        "center_lat": float(center_lat),
        "center_lng": float(center_lng),
        "show_route": bool(show_route),
        "show_numbers": bool(show_numbers),
        "focus_order": int(focus_order or 0),
        "focus_label": focus_label or "",
        "title": title or "Live Kakao Map",
        "height": int(height),
    }
    cfg_js = json.dumps(cfg, ensure_ascii=False)
    safe_focus = html_module.escape(focus_label or "")
    safe_title = html_module.escape(title or "Live Kakao Map")
    badge = f"📍 {safe_focus}" if safe_focus else "일정 카드를 클릭하세요"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8"/>
  <meta name="referrer" content="origin"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; width: 100%; font-family: sans-serif; }}
    .map-shell {{
      background: #fff; border-radius: 22px; padding: 0.75rem;
      border: 1px solid #E2E8F0; box-shadow: 0 12px 36px rgba(13, 148, 136, 0.12);
    }}
    .map-head {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.25rem 0.35rem 0.55rem; gap: 10px; flex-wrap: wrap;
    }}
    .map-label {{ font-weight: 800; color: #134E4A; font-size: 0.88rem; }}
    .map-focus {{
      font-size: 0.7rem; font-weight: 700; color: #fff;
      background: linear-gradient(135deg, #0D9488, #14B8A6);
      padding: 0.35rem 0.7rem; border-radius: 999px; max-width: 72%;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }}
    #map-wrap {{
      width: 100%; position: relative; overflow: hidden;
      border-radius: 16px; background: #F1F5F9; border: 1px solid #E2E8F0;
    }}
    #map-loading {{
      position: absolute; inset: 0; z-index: 5; display: flex; align-items: center;
      justify-content: center; color: #64748B; font-size: 0.85rem; background: #F1F5F9;
    }}
    #map-error {{
      display: none; padding: 8px 10px; color: #92400E; font-size: 11px;
      background: #FFFBEB; border-radius: 10px; margin-bottom: 6px; line-height: 1.45;
    }}
    #map {{ width: 100%; height: {height}px; }}
    .order-pin {{
      background: #14B8A6; color: #fff; font-weight: 700; font-size: 12px;
      width: 26px; height: 26px; border-radius: 50%; display: flex;
      align-items: center; justify-content: center;
      border: 2px solid #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.25);
    }}
    .order-pin.focus {{ background: #E85D04; width: 32px; height: 32px; }}
  </style>
</head>
<body>
  <div class="map-shell">
    <div class="map-head">
      <span class="map-label" id="map-label">{safe_title}</span>
      <span class="map-focus" id="map-focus-badge">{badge}</span>
    </div>
    <div id="map-error"></div>
    <div id="map-wrap">
      <div id="map-loading">카카오 지도 불러오는 중…</div>
      <div id="map"></div>
    </div>
  </div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>const MAP_CONFIG = {cfg_js};</script>
  <script>{_MAP_JS}</script>
  <script>bootMap(MAP_CONFIG);</script>
</body>
</html>"""


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

    html_page = _build_map_html(
        app_key=app_key,
        markers=markers,
        center_lat=center_lat,
        center_lng=center_lng,
        show_route=bool(show_route and len(display_spots) > 1),
        show_numbers=bool(route_spots),
        focus_order=int(focus_order or 0),
        focus_label=focus_label,
        title=title,
        height=height,
    )
    components.html(
        html_page,
        height=height + 88,
        scrolling=False,
        key=f"kakao_map_focus_{focus_order}",
    )

    if not app_key:
        st.info("Secrets에 `KAKAO_MAP_APP_KEY`(JavaScript 키)를 설정하세요.")
    else:
        with st.expander("OpenStreetMap으로만 보이나요?"):
            st.markdown(_DOMAIN_HINT)
            st.caption(
                "앱 안에서는 카카오 iframe 제한으로 OSM이 나올 수 있습니다. "
                "위 **카카오맵에서 전체 동선 보기** 버튼을 이용하세요."
            )
