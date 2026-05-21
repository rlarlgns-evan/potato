import html as html_module
import json
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from config import get_env

_DOMAIN_HINT = (
    "Kakao Developers → JavaScript 키 → SDK 도메인: "
    "<code>https://kangwon-potato.streamlit.app</code>"
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
                "description": "AI 추천 후 마커가 표시됩니다.",
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

    markers_json = json.dumps(markers, ensure_ascii=False)
    show_polyline = "true" if show_route and len(display_spots) > 1 else "false"
    has_numbered = "true" if route_spots else "false"
    focus_order = int(focus_order or 0)
    safe_key = html_module.escape(app_key or "", quote=True)
    safe_title = html_module.escape(title)
    safe_focus = html_module.escape(focus_label or "")
    shell_h = height + 88
    domain_hint_js = json.dumps(_DOMAIN_HINT, ensure_ascii=False)

    appkey_js = json.dumps(app_key) if app_key else '""'

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="referrer" content="origin"/>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; width: 100%;
      font-family: 'Plus Jakarta Sans', sans-serif; }}
    .map-shell {{
      background: #fff; border-radius: 22px; padding: 0.75rem;
      border: 1px solid #E2E8F0; width: 100%;
      box-shadow: 0 12px 36px rgba(13, 148, 136, 0.12);
    }}
    .map-head {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.25rem 0.35rem 0.55rem; gap: 10px; flex-wrap: wrap;
    }}
    .map-label {{
      font-weight: 800; color: #134E4A; font-size: 0.88rem;
      letter-spacing: 0.04em; text-transform: uppercase;
    }}
    .map-focus {{
      font-size: 0.7rem; font-weight: 700; color: #fff;
      background: linear-gradient(135deg, #0D9488, #14B8A6);
      padding: 0.35rem 0.7rem; border-radius: 999px; max-width: 72%;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      box-shadow: 0 4px 12px rgba(20, 184, 166, 0.35);
    }}
    #map-wrap {{
      width: 100%; position: relative; overflow: hidden;
      border-radius: 16px; background: #F1F5F9;
      border: 1px solid #E2E8F0;
    }}
    #map-loading {{
      position: absolute; inset: 0; z-index: 5; display: flex; align-items: center;
      justify-content: center; color: #64748B; font-size: 0.85rem; background: #E2E8F0;
    }}
    #map-error {{
      display: none; padding: 8px 10px; color: #92400E; font-size: 11px;
      background: #FFFBEB; border-radius: 10px; margin-bottom: 6px;
    }}
    #map {{ width: 100%; height: {height}px; }}
    .order-pin {{
      background: #14B8A6; color: #fff; font-weight: 700; font-size: 12px;
      width: 26px; height: 26px; border-radius: 50%; display: flex;
      align-items: center; justify-content: center;
      border: 2px solid #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.25);
    }}
    .order-pin.focus {{
      background: #E85D04; width: 32px; height: 32px; font-size: 13px;
      box-shadow: 0 0 0 4px rgba(232,93,4,0.35);
    }}
    .popup-box {{ min-width: 200px; line-height: 1.5; font-size: 13px; }}
    .popup-box h4 {{ margin: 0 0 6px; color: #134E4A; font-size: 14px; }}
    .popup-meta {{ color: #64748B; font-size: 12px; margin: 0 0 6px; }}
    .popup-why {{ color: #334155; margin: 0 0 6px; }}
    .popup-coord {{ color: #94A3B8; font-size: 11px; margin: 0; }}
  </style>
</head>
<body>
  <div class="map-shell">
    <div class="map-head">
      <span class="map-label" id="map-label">{safe_title}</span>
      <span class="map-focus" id="map-focus-badge">{('📍 ' + safe_focus) if safe_focus else '일정 카드를 클릭하세요'}</span>
    </div>
    <div id="map-error"></div>
    <div id="map-wrap">
      <div id="map-loading">카카오 지도 불러오는 중…</div>
      <div id="map"></div>
    </div>
  </div>
  <script>
    const APPKEY = {appkey_js};
    const markers = {markers_json};
    const showRoute = {show_polyline};
    const showNumbers = {has_numbered};
    const focusOrder = {focus_order};
    const centerLat = {center_lat};
    const centerLng = {center_lng};
    const domainHint = {domain_hint_js};
    const hasKakaoKey = APPKEY && APPKEY.length > 0;

    let mapReady = false;
    let mapEngine = '';

    function showWarn(msg) {{
      const el = document.getElementById('map-error');
      el.style.display = 'block';
      el.innerHTML = msg;
    }}

    function hideLoading() {{
      const el = document.getElementById('map-loading');
      if (el) el.style.display = 'none';
    }}

    function popupHtml(spot, isFocus) {{
      const stay = spot.stay_minutes ? ('약 ' + spot.stay_minutes + '분 체류') : '';
      const move = spot.move_to_next ? ('<p class="popup-meta">🚗 ' + spot.move_to_next + '</p>') : '';
      const why = spot.why ? ('<p class="popup-why">' + spot.why + '</p>') : '';
      return '<div class="popup-box">'
        + '<h4>' + (showNumbers ? spot.order + '. ' : '') + spot.name + (isFocus ? ' ★' : '') + '</h4>'
        + '<p class="popup-meta">' + (spot.region || '') + (spot.theme ? ' · ' + spot.theme : '') + (stay ? ' · ' + stay : '') + '</p>'
        + why
        + '<p class="popup-meta">' + (spot.description || '') + '</p>'
        + move
        + '<p class="popup-coord">좌표 ' + spot.lat.toFixed(5) + ', ' + spot.lng.toFixed(5) + ' (앱 DB 기준)</p>'
        + '</div>';
    }}

    function isFocused(spot) {{
      return focusOrder > 0 && spot.order === focusOrder;
    }}

    function applyFocusView(map, spot, isLeaflet) {{
      if (!spot) return;
      if (isLeaflet) {{
        map.flyTo([spot.lat, spot.lng], 12, {{ duration: 0.6 }});
      }} else {{
        const pos = new kakao.maps.LatLng(spot.lat, spot.lng);
        map.setCenter(pos);
        map.setLevel(5);
      }}
    }}

    function initLeaflet() {{
      if (mapEngine === 'kakao' || mapReady) return;
      mapEngine = 'leaflet';
      hideLoading();

      const container = document.getElementById('map');
      container.innerHTML = '';
      const map = L.map(container).setView([centerLat, centerLng], 9);
      L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 18, attribution: '&copy; OpenStreetMap'
      }}).addTo(map);

      const latlngs = [];
      let focusSpot = null;
      const layerMarkers = [];

      markers.forEach(function(spot) {{
        const ll = [spot.lat, spot.lng];
        latlngs.push(ll);
        const focused = isFocused(spot);
        if (focused) focusSpot = spot;

        const icon = L.divIcon({{
          html: '<div class="order-pin' + (focused ? ' focus' : '') + '">' + (showNumbers ? spot.order : '') + '</div>',
          className: '', iconSize: focused ? [32, 32] : [26, 26],
          iconAnchor: focused ? [16, 16] : [13, 13]
        }});
        const m = L.marker(ll, {{ icon: icon }}).addTo(map);
        m.bindPopup(popupHtml(spot, focused), {{ maxWidth: 280 }});
        m.on('click', function() {{ m.openPopup(); }});
        layerMarkers.push(m);
        if (focused) {{
          m.openPopup();
          applyFocusView(map, spot, true);
        }}
      }});

      if (showRoute && latlngs.length > 1) {{
        L.polyline(latlngs, {{ color: '#14B8A6', weight: 4, opacity: 0.85 }}).addTo(map);
      }}
      if (!focusSpot && latlngs.length > 1) {{
        map.fitBounds(latlngs, {{ padding: [40, 40] }});
      }}

      mapReady = true;
      setTimeout(function() {{ map.invalidateSize(); }}, 200);
      setTimeout(function() {{ map.invalidateSize(); }}, 700);
    }}

    function startFallback(reason) {{
      if (mapReady) return;
      if (reason) showWarn(reason + '<br/><small>' + domainHint + '</small>');
      if (typeof L === 'undefined') {{
        hideLoading();
        showWarn('지도를 불러오지 못했습니다.');
        return;
      }}
      initLeaflet();
    }}

    function kakaoReady() {{
      return typeof kakao !== 'undefined'
        && kakao.maps
        && typeof kakao.maps.LatLng === 'function'
        && typeof kakao.maps.load === 'function';
    }}

    function initKakaoMap() {{
      mapEngine = 'kakao';
      const container = document.getElementById('map');
      container.innerHTML = '';
      const map = new kakao.maps.Map(container, {{
        center: new kakao.maps.LatLng(centerLat, centerLng),
        level: 8
      }});

      const bounds = new kakao.maps.LatLngBounds();
      const path = [];
      let focusSpot = null;

      markers.forEach(function(spot) {{
        const pos = new kakao.maps.LatLng(spot.lat, spot.lng);
        bounds.extend(pos);
        path.push(pos);
        const focused = isFocused(spot);
        if (focused) focusSpot = spot;

        const marker = new kakao.maps.Marker({{ position: pos }});
        marker.setMap(map);

        if (showNumbers && spot.order > 0) {{
          const bg = focused ? '#E85D04' : '#14B8A6';
          const label = '<div style="padding:4px 9px;background:' + bg + ';color:#fff;'
            + 'border-radius:6px;font-size:12px;font-weight:700;">' + spot.order + '</div>';
          new kakao.maps.CustomOverlay({{
            position: pos, content: label, yAnchor: 1.45
          }}).setMap(map);
        }}

        const infowindow = new kakao.maps.InfoWindow({{ content: popupHtml(spot, focused) }});
        kakao.maps.event.addListener(marker, 'click', function() {{
          infowindow.open(map, marker);
        }});

        if (focused) {{
          infowindow.open(map, marker);
          applyFocusView(map, spot, false);
        }}
      }});

      if (showRoute && path.length > 1) {{
        new kakao.maps.Polyline({{
          path: path, strokeWeight: 4, strokeColor: '#14B8A6',
          strokeOpacity: 0.85, strokeStyle: 'solid'
        }}).setMap(map);
      }}

      if (!focusSpot && markers.length > 1) {{
        map.setBounds(bounds);
      }} else if (!focusSpot && markers.length === 1) {{
        map.setCenter(new kakao.maps.LatLng(markers[0].lat, markers[0].lng));
        map.setLevel(7);
      }}

      mapReady = true;
      hideLoading();
      function relayout() {{ map.relayout(); }}
      setTimeout(relayout, 100);
      setTimeout(relayout, 500);
      if (typeof ResizeObserver !== 'undefined') {{
        new ResizeObserver(relayout).observe(document.getElementById('map-wrap'));
      }}
    }}

    function setMapLabel(text) {{
      const el = document.getElementById('map-label');
      if (el) el.textContent = text;
    }}

    function ensureLeafletThenRun(fn) {{
      if (typeof L !== 'undefined') {{
        fn();
        return;
      }}
      const s = document.createElement('script');
      s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      s.onload = fn;
      s.onerror = function() {{
        hideLoading();
        showWarn('대체 지도(OpenStreetMap) 로드 실패');
      }};
      document.head.appendChild(s);
    }}

    function useOsmFallback(msg) {{
      if (mapReady && mapEngine === 'kakao') return;
      if (msg) showWarn(msg + '<br/><small>' + domainHint + '</small>');
      setMapLabel('OpenStreetMap (대체)');
      ensureLeafletThenRun(initLeaflet);
    }}

    function runKakaoMap(onFail, onSuccess) {{
      kakao.maps.load(function() {{
        try {{
          initKakaoMap();
          setMapLabel('Kakao Map');
          onSuccess();
        }} catch (e) {{
          onFail('카카오 지도 오류: ' + e.message);
        }}
      }});
    }}

    function bootKakaoFirst() {{
      if (!hasKakaoKey) {{
        useOsmFallback('KAKAO_MAP_APP_KEY가 없습니다.');
        return;
      }}

      let settled = false;
      const fallbackTimer = setTimeout(function() {{
        if (settled) return;
        settled = true;
        useOsmFallback(
          '카카오 지도 연결 실패. JavaScript SDK 도메인에 '
          + 'https://kangwon-potato.streamlit.app 등록 여부를 확인하세요.'
        );
      }}, 6000);

      function fail(msg) {{
        if (settled) return;
        settled = true;
        clearTimeout(fallbackTimer);
        useOsmFallback(msg);
      }}

      function succeed() {{
        settled = true;
        clearTimeout(fallbackTimer);
      }}

      if (kakaoReady()) {{
        runKakaoMap(fail, succeed);
        return;
      }}

      const sdk = document.createElement('script');
      sdk.src = 'https://dapi.kakao.com/v2/maps/sdk.js?appkey='
        + encodeURIComponent(APPKEY) + '&autoload=false';
      sdk.onload = function() {{
        if (!kakaoReady()) {{
          fail('카카오 SDK 초기화 실패');
          return;
        }}
        runKakaoMap(fail, succeed);
      }};
      sdk.onerror = function() {{ fail('카카오 SDK 네트워크 오류'); }};
      document.head.appendChild(sdk);
    }}

    bootKakaoFirst();
  </script>
</body>
</html>"""

    components.html(html_content, height=shell_h, scrolling=False)
