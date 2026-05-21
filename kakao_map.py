import json
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from config import get_env


def get_kakao_app_key() -> str:
    # Streamlit 재실행 시에도 프로젝트 루트 .env를 확실히 읽음
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
    empty_message: str = "AI 추천 후 지도에 동선이 표시됩니다.",
) -> None:
    if not app_key:
        st.warning(
            "카카오 지도 API 키가 없습니다. `.env` 또는 Streamlit Secrets에 "
            "`KAKAO_MAP_APP_KEY`를 설정해 주세요."
        )
        st.caption(
            "[카카오 개발자](https://developers.kakao.com) → 앱 → 플랫폼 키 → "
            "JavaScript 키 발급 후, SDK 도메인에 `http://localhost:8501`과 "
            "배포 URL(예: `https://본인앱.streamlit.app`)을 등록하세요."
        )
        return

    display_spots = route_spots if route_spots else spots
    if not display_spots:
        st.info(empty_message)
        return

    markers = []
    for idx, s in enumerate(display_spots, start=1):
        markers.append(
            {
                "name": s["name"],
                "lat": s["lat"],
                "lng": s["lng"],
                "region": s["region"],
                "theme": s["theme"],
                "description": s["description"],
                "order": idx,
            }
        )

    markers_json = json.dumps(markers, ensure_ascii=False)
    show_polyline = "true" if show_route and len(display_spots) > 1 else "false"
    level = 8

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <style>#map {{ width: 100%; height: {height}px; }}</style>
</head>
<body>
  <div id="map"></div>
  <script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={app_key}"></script>
  <script>
    const markers = {markers_json};
    const showRoute = {show_polyline};
    const container = document.getElementById('map');
    const map = new kakao.maps.Map(container, {{
      center: new kakao.maps.LatLng({center_lat}, {center_lng}),
      level: {level}
    }});

    const bounds = new kakao.maps.LatLngBounds();
    const path = [];

    markers.forEach(function(spot) {{
      const pos = new kakao.maps.LatLng(spot.lat, spot.lng);
      bounds.extend(pos);
      path.push(pos);

      const markerImage = new kakao.maps.MarkerImage(
        'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png',
        new kakao.maps.Size(36, 42),
        {{ offset: new kakao.maps.Point(18, 42) }}
      );
      const marker = new kakao.maps.Marker({{
        position: pos,
        image: markerImage
      }});
      marker.setMap(map);

      const content = '<div style="padding:8px;min-width:180px;line-height:1.5;">'
        + '<strong>' + spot.order + '. ' + spot.name + '</strong><br/>'
        + '지역: ' + spot.region + '<br/>'
        + '테마: ' + spot.theme + '<br/>'
        + spot.description
        + '</div>';
      const infowindow = new kakao.maps.InfoWindow({{ content: content }});
      kakao.maps.event.addListener(marker, 'click', function() {{
        infowindow.open(map, marker);
      }});
    }});

    if (showRoute && path.length > 1) {{
      const polyline = new kakao.maps.Polyline({{
        path: path,
        strokeWeight: 4,
        strokeColor: '#E85D04',
        strokeOpacity: 0.85,
        strokeStyle: 'solid'
      }});
      polyline.setMap(map);
    }}

    if (markers.length > 1) {{
      map.setBounds(bounds);
    }} else if (markers.length === 1) {{
      map.setCenter(new kakao.maps.LatLng(markers[0].lat, markers[0].lng));
      map.setLevel(5);
    }}
  </script>
</body>
</html>"""

    components.html(html_content, height=height + 16)
