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
    head_html = ""  # 헤더/포커스 칩은 app.py(render_planner_map_chrome)에서 표시

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8"/>
  <meta name="referrer" content="origin"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; width: 100%; font-family: 'Inter', system-ui, sans-serif; }}
    .map-shell {{ background: transparent; }}
    .map-head {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.1rem 0.2rem 0.55rem; gap: 10px; flex-wrap: wrap;
    }}
    .map-label {{ font-weight: 800; color: #006a61; font-size: 0.88rem; }}
    .map-focus {{
      font-size: 0.7rem; font-weight: 700; color: #004a43;
      background: #66bcb0; padding: 0.32rem 0.7rem; border-radius: 999px; max-width: 72%;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }}
    #map-wrap {{
      width: 100%; position: relative; overflow: hidden;
      border-radius: 18px; background: #eef3f2; border: 1px solid #bdc9c6;
      box-shadow: 0 6px 24px rgba(0,106,97,0.07);
    }}
    #map-loading {{
      position: absolute; inset: 0; z-index: 5; display: flex; align-items: center;
      justify-content: center; color: #3e4947; font-size: 0.85rem; background: #eef3f2;
    }}
    #map {{ width: 100%; height: {height}px; }}
    .leaflet-container {{ font-family: 'Inter', sans-serif; background: #eef3f2; }}
    .leaflet-popup-content-wrapper {{ border-radius: 14px; box-shadow: 0 8px 28px rgba(0,0,0,0.14); }}
    .order-pin {{
      background: #006a61; color: #fff; font-weight: 800; font-size: 12px;
      width: 28px; height: 28px; border-radius: 50% 50% 50% 4px; display: flex;
      align-items: center; justify-content: center; transform: rotate(0deg);
      border: 2.5px solid #fff; box-shadow: 0 3px 8px rgba(0,0,0,0.28);
    }}
    .order-pin.focus {{
      background: #004a43; width: 34px; height: 34px;
      box-shadow: 0 0 0 5px rgba(102,188,176,0.4), 0 3px 10px rgba(0,0,0,0.3);
    }}
  </style>
</head>
<body>
  <div class="map-shell">
    {head_html}
    <div id="map-wrap">
      <div id="map-loading">지도 불러오는 중…</div>
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
    # key= 는 일부 Cloud Streamlit 버전에서 TypeError → HTML 주석으로 focus 갱신
    components.html(
        f"<!-- map-focus-{int(focus_order or 0)} -->\n{html_page}",
        height=height + 70,
        scrolling=False,
    )
