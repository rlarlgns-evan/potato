import html as html_module
import json
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from config import get_env

_DOMAIN_HINT = (
    "Kakao Developers → 앱 → JavaScript 키 → Web 플랫폼에 "
    "`http://localhost:8501` 과 Streamlit 배포 주소(예: `https://xxxx.streamlit.app`)를 등록하세요."
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
    if not app_key:
        st.warning(
            "카카오 지도 API 키가 없습니다. `.env` 또는 Streamlit Secrets에 "
            "`KAKAO_MAP_APP_KEY`(JavaScript 키)를 설정해 주세요."
        )
        return

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
    safe_key = html_module.escape(app_key, quote=True)
    safe_title = html_module.escape(title)
    shell_h = height + 56

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="referrer" content="origin"/>
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
      width: 100%; min-width: 260px; min-height: {height}px;
      position: relative; overflow: hidden; border-radius: 14px;
      background: #E2E8F0;
    }}
    #map {{ width: 100%; height: {height}px; }}
    #map-error {{
      display: none; padding: 12px; color: #b42318; font-size: 13px;
      line-height: 1.55; background: #FEF2F2; border-radius: 12px;
      margin-bottom: 8px;
    }}
    #map-loading {{
      position: absolute; inset: 0; display: flex; align-items: center;
      justify-content: center; color: #64748B; font-size: 0.85rem;
      pointer-events: none;
    }}
  </style>
</head>
<body>
  <div class="map-shell">
    <div class="map-label">{safe_title}</div>
    <div id="map-error"></div>
    <div id="map-wrap">
      <div id="map-loading">지도 불러오는 중…</div>
      <div id="map"></div>
    </div>
  </div>
  <script>
    const APPKEY = "{safe_key}";
    const markers = {markers_json};
    const showRoute = {show_polyline};
    const showNumbers = {has_numbered};
    const focusOrder = {focus_order};
    const domainHint = {_DOMAIN_HINT!r};

    function showError(msg) {{
      const el = document.getElementById('map-error');
      const loading = document.getElementById('map-loading');
      if (loading) loading.style.display = 'none';
      el.style.display = 'block';
      el.innerHTML = msg;
    }}

    function hideLoading() {{
      const loading = document.getElementById('map-loading');
      if (loading) loading.style.display = 'none';
    }}

    function initMap() {{
      try {{
        const container = document.getElementById('map');
        const map = new kakao.maps.Map(container, {{
          center: new kakao.maps.LatLng({center_lat}, {center_lng}),
          level: 8
        }});

        const bounds = new kakao.maps.LatLngBounds();
        const path = [];

        markers.forEach(function(spot) {{
          const pos = new kakao.maps.LatLng(spot.lat, spot.lng);
          bounds.extend(pos);
          path.push(pos);

          const marker = new kakao.maps.Marker({{ position: pos }});
          marker.setMap(map);

          if (showNumbers && spot.order > 0) {{
            const label = '<div style="padding:4px 8px;background:#14B8A6;color:#fff;border-radius:4px;font-size:12px;font-weight:700;">'
              + spot.order + '</div>';
            new kakao.maps.CustomOverlay({{
              position: pos, content: label, yAnchor: 1.4
            }}).setMap(map);
          }}

          const content = '<div style="padding:8px;min-width:180px;line-height:1.5;">'
            + '<strong>' + (showNumbers ? spot.order + '. ' : '') + spot.name + '</strong><br/>'
            + (spot.region ? '지역: ' + spot.region + '<br/>' : '')
            + (spot.theme ? '테마: ' + spot.theme + '<br/>' : '')
            + spot.description + '</div>';
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

        function relayout() {{ map.relayout(); }}
        hideLoading();
        setTimeout(relayout, 100);
        setTimeout(relayout, 400);
        setTimeout(relayout, 1200);
        if (typeof ResizeObserver !== 'undefined') {{
          new ResizeObserver(relayout).observe(document.getElementById('map-wrap'));
        }}
        window.addEventListener('resize', relayout);
      }} catch (e) {{
        showError('지도 초기화 실패: ' + e.message + '<br/><small>' + domainHint + '</small>');
      }}
    }}

    function bootKakao() {{
      if (typeof kakao === 'undefined' || !kakao.maps) {{
        showError(
          '카카오 지도 SDK를 불러오지 못했습니다.<br/>'
          + '① JavaScript 키가 맞는지 ② Web 도메인 등록 여부를 확인하세요.<br/>'
          + '<small>' + domainHint + '</small>'
        );
        return;
      }}
      kakao.maps.load(initMap);
    }}

    const sdk = document.createElement('script');
    sdk.src = 'https://dapi.kakao.com/v2/maps/sdk.js?appkey=' + encodeURIComponent(APPKEY) + '&autoload=false';
    sdk.async = true;
    sdk.onload = bootKakao;
    sdk.onerror = function() {{
      showError('카카오 SDK 네트워크 로드 실패. 배포 URL이 Web 플랫폼에 등록됐는지 확인하세요.<br/><small>' + domainHint + '</small>');
    }};
    setTimeout(function() {{
      if (typeof kakao === 'undefined') {{
        showError('지도 로드 시간 초과. 카카오 JavaScript 키·도메인 설정을 확인하세요.<br/><small>' + domainHint + '</small>');
      }}
    }}, 12000);
    document.head.appendChild(sdk);
  </script>
</body>
</html>"""

    components.html(html_content, height=shell_h, scrolling=False)
