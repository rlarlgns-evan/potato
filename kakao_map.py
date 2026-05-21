import html as html_module
import json
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from config import get_env

# 카카오 지도 JS API 공식 가이드: developers.kakao.com → 플랫폼 키 → JavaScript SDK 도메인
_DOMAIN_HINT = (
    "① <a href='https://developers.kakao.com' target='_blank'>developers.kakao.com</a> "
    "→ 앱 → <b>플랫폼 키</b> → JavaScript 키<br/>"
    "② <b>JavaScript SDK 도메인</b>에 "
    "<code>http://localhost:8501</code>, "
    "<code>https://본인앱.streamlit.app</code> 등록<br/>"
    "③ JavaScript 키를 Secrets <code>KAKAO_MAP_APP_KEY</code>에 저장"
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


def render_kakao_map(
    spots: list[dict[str, Any]],
    center_lat: float,
    center_lng: float,
    app_key: str,
    height: int = 500,
    route_spots: list[dict[str, Any]] | None = None,
    show_route: bool = False,
    focus_order: int = 0,
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
                "description": (s.get("description") or "")[:200],
                "order": idx,
            }
        )

    markers_json = json.dumps(markers, ensure_ascii=False)
    show_polyline = "true" if show_route and len(display_spots) > 1 else "false"
    has_numbered = "true" if route_spots else "false"
    focus_order = int(focus_order or 0)
    safe_key = html_module.escape(app_key or "", quote=True)
    safe_title = html_module.escape(title)
    shell_h = height + 72
    domain_hint_js = json.dumps(_DOMAIN_HINT, ensure_ascii=False)

    # 공식 문서: SDK script → 바로 new kakao.maps.Map (autoload 기본값, autoload=false 미사용)
    kakao_sdk_script = ""
    if app_key:
        kakao_sdk_script = (
            f'<script type="text/javascript" '
            f'src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={safe_key}"></script>'
        )

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Kakao Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0; padding: 0; width: 100%; min-width: 280px;
      font-family: 'Plus Jakarta Sans', sans-serif;
    }}
    .map-shell {{
      background: #fff; border-radius: 20px; padding: 0.6rem;
      box-shadow: 0 10px 30px rgba(13, 148, 136, 0.1);
      border: 1px solid #CCFBF1; width: 100%;
    }}
    .map-label {{
      padding: 0.35rem 0.5rem 0.5rem; font-weight: 700; color: #134E4A;
      font-size: 0.95rem;
    }}
    #map-wrap {{
      width: 100%; min-width: 260px; position: relative;
      overflow: hidden; border-radius: 14px; background: #E2E8F0;
    }}
    #map-loading {{
      position: absolute; inset: 0; z-index: 2; display: flex; align-items: center;
      justify-content: center; color: #64748B; font-size: 0.85rem;
      background: #E2E8F0; pointer-events: none;
    }}
    #map-error {{
      display: none; padding: 10px 12px; color: #92400E; font-size: 12px;
      line-height: 1.5; background: #FFFBEB; border-radius: 12px;
      margin-bottom: 8px; border: 1px solid #FDE68A;
    }}
    .leaflet-popup-content {{ font-size: 13px; line-height: 1.45; margin: 8px 10px; }}
    .order-pin {{
      background: #14B8A6; color: #fff; font-weight: 700; font-size: 12px;
      width: 26px; height: 26px; border-radius: 50%; display: flex;
      align-items: center; justify-content: center;
      border: 2px solid #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.25);
    }}
  </style>
</head>
<body>
  <div class="map-shell">
    <div class="map-label" id="map-title">{safe_title}</div>
    <div id="map-error"></div>
    <div id="map-wrap">
      <div id="map-loading">지도 불러오는 중…</div>
      <!-- 공식 가이드: 지도 영역 DOM (고정 높이 필수) -->
      <div id="map" style="width:100%;height:{height}px;"></div>
    </div>
  </div>
  {kakao_sdk_script}
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const markers = {markers_json};
    const showRoute = {show_polyline};
    const showNumbers = {has_numbered};
    const focusOrder = {focus_order};
    const centerLat = {center_lat};
    const centerLng = {center_lng};
    const domainHint = {domain_hint_js};
    const hasKakaoKey = {str(bool(app_key)).lower()};

    let mapReady = false;
    let fallbackDone = false;

    function showWarn(msg) {{
      const el = document.getElementById('map-error');
      el.style.display = 'block';
      el.innerHTML = msg;
    }}

    function hideLoading() {{
      const el = document.getElementById('map-loading');
      if (el) el.style.display = 'none';
    }}

    function popupHtml(spot) {{
      return '<strong>' + (showNumbers ? spot.order + '. ' : '') + spot.name + '</strong><br/>'
        + (spot.region ? spot.region + ' · ' : '')
        + (spot.theme || '') + '<br/>' + (spot.description || '');
    }}

    function initLeaflet() {{
      if (fallbackDone) return;
      fallbackDone = true;
      hideLoading();
      document.getElementById('map-title').textContent = 'Trip Map';

      const container = document.getElementById('map');
      container.innerHTML = '';
      container.style.height = '{height}px';

      const map = L.map(container).setView([centerLat, centerLng], 9);
      L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 18, attribution: '&copy; OpenStreetMap'
      }}).addTo(map);

      const latlngs = [];
      markers.forEach(function(spot) {{
        const ll = [spot.lat, spot.lng];
        latlngs.push(ll);
        const icon = (showNumbers && spot.order > 0)
          ? L.divIcon({{
              html: '<div class="order-pin">' + spot.order + '</div>',
              className: '', iconSize: [26, 26], iconAnchor: [13, 13]
            }})
          : L.divIcon({{
              html: '<div class="order-pin" style="width:14px;height:14px;"></div>',
              className: '', iconSize: [14, 14], iconAnchor: [7, 7]
            }});
        const m = L.marker(ll, {{ icon: icon }}).addTo(map);
        m.bindPopup(popupHtml(spot));
        if (focusOrder > 0 && spot.order === focusOrder) {{
          map.setView(ll, 11);
          m.openPopup();
        }}
      }});

      if (showRoute && latlngs.length > 1) {{
        L.polyline(latlngs, {{ color: '#14B8A6', weight: 4, opacity: 0.85 }}).addTo(map);
      }}
      if (latlngs.length > 1) map.fitBounds(latlngs, {{ padding: [36, 36] }});

      mapReady = true;
      setTimeout(function() {{ map.invalidateSize(); }}, 200);
      setTimeout(function() {{ map.invalidateSize(); }}, 700);
    }}

    function startFallback(reason) {{
      if (mapReady || fallbackDone) return;
      if (reason) showWarn(reason + '<br/><small>' + domainHint + '</small>');
      if (typeof L === 'undefined') {{
        hideLoading();
        showWarn('지도 라이브러리 로드 실패.');
        return;
      }}
      initLeaflet();
    }}

    /* 카카오 공식 샘플과 동일: container + options → new kakao.maps.Map */
    function initKakaoMap() {{
      const container = document.getElementById('map');
      const options = {{
        center: new kakao.maps.LatLng(centerLat, centerLng),
        level: 8
      }};
      const map = new kakao.maps.Map(container, options);

      const bounds = new kakao.maps.LatLngBounds();
      const path = [];

      markers.forEach(function(spot) {{
        const pos = new kakao.maps.LatLng(spot.lat, spot.lng);
        bounds.extend(pos);
        path.push(pos);

        const marker = new kakao.maps.Marker({{ position: pos }});
        marker.setMap(map);

        if (showNumbers && spot.order > 0) {{
          const label = '<div style="padding:4px 8px;background:#14B8A6;color:#fff;'
            + 'border-radius:4px;font-size:12px;font-weight:700;">' + spot.order + '</div>';
          new kakao.maps.CustomOverlay({{
            position: pos, content: label, yAnchor: 1.4
          }}).setMap(map);
        }}

        const content = '<div style="padding:8px;min-width:180px;line-height:1.5;">'
          + popupHtml(spot) + '</div>';
        const infowindow = new kakao.maps.InfoWindow({{ content: content }});
        kakao.maps.event.addListener(marker, 'click', function() {{
          infowindow.open(map, marker);
        }});

        if (focusOrder > 0 && spot.order === focusOrder) {{
          infowindow.open(map, marker);
          map.setCenter(pos);
          map.setLevel(6);
        }}
      }});

      if (showRoute && path.length > 1) {{
        new kakao.maps.Polyline({{
          path: path, strokeWeight: 4, strokeColor: '#14B8A6',
          strokeOpacity: 0.85, strokeStyle: 'solid'
        }}).setMap(map);
      }}

      if (markers.length > 1) {{
        map.setBounds(bounds);
      }} else if (markers.length === 1) {{
        map.setCenter(new kakao.maps.LatLng(markers[0].lat, markers[0].lng));
        map.setLevel(7);
      }}

      mapReady = true;
      fallbackDone = true;
      hideLoading();
      function relayout() {{ map.relayout(); }}
      setTimeout(relayout, 100);
      setTimeout(relayout, 500);
      if (typeof ResizeObserver !== 'undefined') {{
        new ResizeObserver(relayout).observe(document.getElementById('map-wrap'));
      }}
    }}

    function tryKakaoOfficial() {{
      if (!hasKakaoKey) {{
        startFallback('JavaScript 키가 없어 OpenStreetMap으로 표시합니다.');
        return;
      }}

      const loadTimeout = setTimeout(function() {{
        if (!mapReady) {{
          startFallback(
            '카카오 지도 로드 실패 (SDK 도메인 미등록 가능). OpenStreetMap으로 표시합니다.'
          );
        }}
      }}, 5000);

      try {{
        if (typeof kakao === 'undefined' || !kakao.maps) {{
          clearTimeout(loadTimeout);
          startFallback('카카오 SDK를 불러오지 못했습니다.');
          return;
        }}
        initKakaoMap();
        clearTimeout(loadTimeout);
      }} catch (e) {{
        clearTimeout(loadTimeout);
        startFallback('카카오 지도 오류: ' + e.message);
      }}
    }}

    tryKakaoOfficial();
  </script>
</body>
</html>"""

    components.html(html_content, height=shell_h, scrolling=False)

    if not app_key:
        st.info(
            "카카오 **JavaScript 키**가 없습니다. "
            "[developers.kakao.com](https://developers.kakao.com)에서 키 발급 후 "
            "Secrets `KAKAO_MAP_APP_KEY`에 넣고, **JavaScript SDK 도메인**에 "
            "`http://localhost:8501`과 Streamlit 배포 URL을 등록하세요."
        )
