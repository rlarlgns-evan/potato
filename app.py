import config  # noqa: F401 — .env 로드

import streamlit as st

from chatbot import curate_trip
from database import get_filter_options, get_spots, init_db
from kakao_map import get_kakao_app_key, render_kakao_map
from ui import (
    hero_header,
    inject_styles,
    map_card_close,
    map_card_open,
    render_spot_carousel,
    render_step_ticket,
    render_theme_chips,
    section_title,
)

st.set_page_config(
    page_title="샤이한 열정 감자들",
    page_icon="🥔",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()
init_db()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "안녕하세요! 🥔\n\n"
                "여행 **기간·동반자·분위기**를 알려주시면 "
                "방문 순서가 있는 **당일/반나절 코스**를 짜고 카카오맵에 표시해 드려요."
            ),
        }
    ]
if "curated_spots" not in st.session_state:
    st.session_state.curated_spots = []
if "route_steps" not in st.session_state:
    st.session_state.route_steps = []
if "itinerary_meta" not in st.session_state:
    st.session_state.itinerary_meta = {}

kakao_key = get_kakao_app_key()

with st.sidebar:
    st.markdown("### 🥔 Trip Filters")
    regions, themes = get_filter_options()
    st.markdown("**지역**")
    selected_region = st.selectbox("지역", ["전체"] + regions, label_visibility="collapsed")
    st.markdown("**테마**")
    selected_theme = st.selectbox("테마", ["전체"] + themes, label_visibility="collapsed")
    st.caption("AI가 고를 후보 장소 범위")
    if not kakao_key:
        st.warning("KAKAO_MAP_APP_KEY 필요")

candidate_spots = get_spots(region=selected_region, theme=selected_theme)

hero_header()
render_theme_chips()

if not st.session_state.curated_spots:
    render_spot_carousel(candidate_spots)

# --- 메인 2열: 채팅 | 결과 ---
chat_col, result_col = st.columns([1, 1.12], gap="large")

with chat_col:
    st.markdown('<div class="surface-card">', unsafe_allow_html=True)
    section_title("Plan Your Trip", "취향을 입력하면 AI가 동선을 설계합니다")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_prompt = st.chat_input("Search routes, moods, companions…")
    st.markdown("</div>", unsafe_allow_html=True)

    if user_prompt:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.spinner("Designing your route…"):
            result = curate_trip(
                user_message=user_prompt,
                spots=candidate_spots,
                chat_history=st.session_state.messages,
            )
        st.session_state.messages.append({"role": "assistant", "content": result["message"]})
        st.session_state.curated_spots = result["curated_spots"]
        st.session_state.route_steps = result.get("route_steps", [])
        st.session_state.itinerary_meta = {
            "title": result.get("itinerary_title", ""),
            "summary": result.get("summary", ""),
            "map_tip": result.get("map_tip", ""),
            "total_duration": result.get("total_duration", ""),
        }
        st.rerun()

curated = st.session_state.curated_spots
meta = st.session_state.itinerary_meta
steps = st.session_state.route_steps

if curated:
    center_lat = sum(s["lat"] for s in curated) / len(curated)
    center_lng = sum(s["lng"] for s in curated) / len(curated)
elif candidate_spots:
    center_lat = sum(s["lat"] for s in candidate_spots) / len(candidate_spots)
    center_lng = sum(s["lng"] for s in candidate_spots) / len(candidate_spots)
else:
    center_lat, center_lng = 37.8228, 128.1555

with result_col:
    if curated:
        st.markdown('<div class="surface-card">', unsafe_allow_html=True)
        section_title("Select Route", "추천 코스 · 지도 번호와 연동")

        title = meta.get("title") or "AI 추천 코스"
        st.markdown(f"**{title}**")
        if meta.get("summary"):
            st.caption(meta["summary"])
        if meta.get("total_duration"):
            st.markdown(
                f'<span class="stat-pill">⏱ {meta["total_duration"]}</span>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        for step in steps:
            spot = next((s for s in curated if s["name"] == step["spot_name"]), None)
            render_step_ticket(step, spot)

        if meta.get("map_tip"):
            st.markdown(
                f'<div class="surface-card" style="background:#F0FDF4;border-color:#BBF7D0;">'
                f'<p style="margin:0;color:#166534;font-size:0.88rem;">🗺️ {meta["map_tip"]}</p></div>',
                unsafe_allow_html=True,
            )

        map_card_open("Kakao Map", "번호 = 방문 순서 · 주황선 = 이동 경로")
        render_kakao_map(
            spots=candidate_spots,
            center_lat=center_lat,
            center_lng=center_lng,
            app_key=kakao_key,
            height=420,
            route_spots=curated,
            show_route=len(curated) > 1,
        )
        map_card_close()
    else:
        section_title("Explore Map", "채팅 입력 후 동선이 표시됩니다")
        map_card_open("Kakao Map", "후보 여행지 · AI 추천 시 동선 갱신")
        render_kakao_map(
            spots=candidate_spots,
            center_lat=center_lat,
            center_lng=center_lng,
            app_key=kakao_key,
            height=480,
        )
        map_card_close()

        st.markdown(
            '<div class="surface-card" style="text-align:center;padding:1.5rem;">'
            '<p style="margin:0;color:#64748B;font-size:0.9rem;">'
            "👆 왼쪽에서 여행 취향을 입력하면<br><strong>티켓형 동선 카드</strong>와 지도가 채워집니다."
            "</p></div>",
            unsafe_allow_html=True,
        )

with st.expander("전체 후보지", expanded=False):
    for spot in candidate_spots:
        st.markdown(f"- **{spot['name']}** ({spot['region']}, {spot['theme']})")
