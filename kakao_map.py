import json
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from config import get_env


def get_kakao_app_key() -> str:
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
    key = get_env("KAKAO_MAP_APP_KEY")
    if key:
        return key
    try:
        return str(st.secrets["KAKAO_MAP_APP_KEY"]).strip()
    except Exception:
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
) -> None:
    if not app_key:
        st.warning(
            "카카오 지도 API 키가 없습니다. `.env` 또는 Streamlit Secrets에 "
            "`KAKAO_MAP_APP_KEY`를 설정해 주세요."
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
                "lat": s["lat"],
                "lng": s["lng"],
                "region": s.get("region", ""),
                "theme": s.get("theme", ""),
                "description": s.get("description", ""),
                "order": idx if s.get("order", 1) else idx,
            }
        )

    markers_json = json.dumps(markers, ensure_ascii=False)
    show_polyline = "true" if show_route and len(display_spots) > 1 else "false"
    has_numbered = "true" if route_spots else "false"
    focus_order = int(focus_order or 0)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <style>
    html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; }}
    #map {{ width: 100%; height: {height}px; border-radius: 14px; }}
    #map-error {{
      display: none;
      padding: 12px;
      color: #b42318;
      font-size: 14px;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div id="map-error"></div>
  <div id="map"></div>
  <script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={app_key}&autoload=false"></script>
  <script>
    const markers = {markers_json};
    const showRoute = {show_polyline};
    const showNumbers = {has_numbered};
    const focusOrder = {focus_order};

    function showError(msg) {{
      const el = document.getElementById('map-error');
      el.style.display = 'block';
      el.textContent = msg;
    }}

    kakao.maps.load(function() {{
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
            const label = '<div style="padding:4px 8px;background:#E85D04;color:#fff;border-radius:4px;font-size:12px;">'
              + spot.order + '</div>';
            const overlay = new kakao.maps.CustomOverlay({{
              position: pos,
              content: label,
              yAnchor: 1.4
            }});
            overlay.setMap(map);
          }}

          const content = '<div style="padding:8px;min-width:180px;line-height:1.5;">'
            + '<strong>' + (showNumbers ? spot.order + '. ' : '') + spot.name + '</strong><br/>'
            + (spot.region ? '지역: ' + spot.region + '<br/>' : '')
            + (spot.theme ? '테마: ' + spot.theme + '<br/>' : '')
            + spot.description
            + '</div>';
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
            path: path,
            strokeWeight: 4,
            strokeColor: '#14B8A6',
            strokeOpacity: 0.85,
            strokeStyle: 'solid'
          }}).setMap(map);
        }}

        if (markers.length > 1) {{
          map.setBounds(bounds);
        }} else {{
          map.setCenter(new kakao.maps.LatLng(markers[0].lat, markers[0].lng));
          map.setLevel(7);
        }}

        setTimeout(function() {{ map.relayout(); }}, 200);
        setTimeout(function() {{ map.relayout(); }}, 800);
      }} catch (e) {{
        showError('지도 초기화 실패: ' + e.message);
      }}
    }});
  </script>
</body>
</html>"""

    components.html(html_content, height=height + 16, scrolling=False)
