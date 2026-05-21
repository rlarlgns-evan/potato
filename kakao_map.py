import json
import os
from typing import Any

import streamlit as st
import streamlit.components.v1 as components


def get_kakao_app_key() -> str:
    try:
        key = st.secrets.get("KAKAO_MAP_APP_KEY", "")
        if key:
            return str(key).strip()
    except Exception:
        pass
    return os.getenv("KAKAO_MAP_APP_KEY", "").strip()


def render_kakao_map(
    spots: list[dict[str, Any]],
    center_lat: float,
    center_lng: float,
    app_key: str,
    height: int = 500,
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

    markers = [
        {
            "name": s["name"],
            "lat": s["lat"],
            "lng": s["lng"],
            "region": s["region"],
            "theme": s["theme"],
            "description": s["description"],
        }
        for s in spots
    ]
    markers_json = json.dumps(markers, ensure_ascii=False)
    level = 9 if not spots else 8

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
    const container = document.getElementById('map');
    const map = new kakao.maps.Map(container, {{
      center: new kakao.maps.LatLng({center_lat}, {center_lng}),
      level: {level}
    }});

    if (markers.length === 0) {{
      return;
    }}

    const bounds = new kakao.maps.LatLngBounds();
    markers.forEach(function(spot) {{
      const pos = new kakao.maps.LatLng(spot.lat, spot.lng);
      bounds.extend(pos);
      const marker = new kakao.maps.Marker({{ position: pos }});
      marker.setMap(map);
      const content = '<div style="padding:8px;min-width:160px;line-height:1.5;">'
        + '<strong>' + spot.name + '</strong><br/>'
        + '지역: ' + spot.region + '<br/>'
        + '테마: ' + spot.theme + '<br/>'
        + spot.description
        + '</div>';
      const infowindow = new kakao.maps.InfoWindow({{ content: content }});
      kakao.maps.event.addListener(marker, 'click', function() {{
        infowindow.open(map, marker);
      }});
    }});

    if (markers.length > 1) {{
      map.setBounds(bounds);
    }} else {{
      map.setCenter(new kakao.maps.LatLng(markers[0].lat, markers[0].lng));
      map.setLevel(5);
    }}
  </script>
</body>
</html>"""

    components.html(html_content, height=height + 16)
