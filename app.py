import config  # noqa: F401 — .env 로드

import streamlit as st

from chatbot import curate_trip
from database import get_all_spots, init_db
from gangwon_content import get_region_intro
from kakao_map import (
    build_kakao_route_url,
    build_route_markers,
    get_kakao_app_key,
    render_kakao_map,
)
from ui import (
    inject_styles,
    render_app_header,
    render_featured_trip,
    render_gangwon_dashboard,
    render_home_search_hero,
    render_screen_steps,
    render_clickable_spot_card,
    render_trip_information,
)

st.set_page_config(
    page_title="샤이한 열정 감자들",
    page_icon="🥔",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_styles()
init_db()

ALL_SPOTS = get_all_spots()

if "screen" not in st.session_state:
    st.session_state.screen = "home"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "curated_spots" not in st.session_state:
    st.session_state.curated_spots = []
if "route_steps" not in st.session_state:
    st.session_state.route_steps = []
if "itinerary_meta" not in st.session_state:
    st.session_state.itinerary_meta = {}
if "focus_order" not in st.session_state:
    st.session_state.focus_order = 1
if "last_user_query" not in st.session_state:
    st.session_state.last_user_query = ""

kakao_key = get_kakao_app_key()


def _map_center(spots: list) -> tuple[float, float]:
    if spots:
        return (
            sum(s["lat"] for s in spots) / len(spots),
            sum(s["lng"] for s in spots) / len(spots),
        )
    return 37.8228, 128.1555


def _apply_curation_result(result: dict, user_prompt: str) -> None:
    st.session_state.last_user_query = user_prompt
    st.session_state.curated_spots = result["curated_spots"]
    st.session_state.route_steps = result.get("route_steps", [])
    st.session_state.itinerary_meta = {
        "title": result.get("itinerary_title", ""),
        "summary": result.get("summary", ""),
        "map_tip": result.get("map_tip", ""),
        "total_duration": result.get("total_duration", ""),
        "message": result.get("message", ""),
    }
    st.session_state.focus_order = 1
    if result["curated_spots"]:
        st.session_state.screen = "results"


# =============================================================================
# ① 홈 — 강원도 정보 + AI 검색
# =============================================================================
if st.session_state.screen == "home":
    render_app_header()
    render_screen_steps(1)
    render_home_search_hero()
    render_gangwon_dashboard()

    with st.form("ai_trip_search", clear_on_submit=True):
        st.markdown("##### 🔍 AI 여행 검색")
        user_prompt = st.text_input(
            "label",
            placeholder="예: 주말 가족과 드라이브, 설악·동해 쪽 당일 코스",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("AI 코스 설계하기", type="primary", use_container_width=True)

    if submitted and user_prompt.strip():
        st.session_state.messages = [
            {"role": "user", "content": user_prompt.strip()},
        ]
        with st.spinner("강원도 전역 관광지에서 동선을 설계하는 중…"):
            result = curate_trip(
                user_message=user_prompt.strip(),
                spots=ALL_SPOTS,
                chat_history=[],
            )
        st.session_state.messages.append(
            {"role": "assistant", "content": result["message"]}
        )
        _apply_curation_result(result, user_prompt.strip())
        st.rerun()

    st.caption(f"등록 관광지 **{len(ALL_SPOTS)}곳** · AI는 필터 없이 강원도 전역에서 선택합니다.")

# =============================================================================
# ② MY TRIP — AI 답변 기반 인터랙티브 동선
# =============================================================================
else:
    curated = st.session_state.curated_spots
    if not curated:
        st.session_state.screen = "home"
        st.rerun()

    meta = st.session_state.itinerary_meta
    steps = st.session_state.route_steps

    render_app_header()
    render_screen_steps(2)

    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if st.button("← 홈", use_container_width=True):
            st.session_state.screen = "home"
            st.rerun()
    with nav2:
        q = st.session_state.last_user_query
        q_prev = (q[:40] + "…") if len(q) > 40 else q
        st.markdown(f"**MY TRIP** · _{q_prev}_")
    with nav3:
        if meta.get("total_duration"):
            st.caption(f"⏱ {meta['total_duration']}")

    render_featured_trip(curated[0], meta)

    route_for_map = build_route_markers(curated, steps)
    focus_spot = next(
        (m for m in route_for_map if m["order"] == st.session_state.focus_order),
        route_for_map[0] if route_for_map else None,
    )
    focus_label = (
        f"STEP {focus_spot['order']} · {focus_spot['name']}" if focus_spot else ""
    )

    left, right = st.columns([1, 1.1], gap="large")

    with left:
        st.markdown(
            '<p class="section-head">Your Route</p>'
            '<p class="section-sub">카드를 탭하면 오른쪽 지도가 해당 장소로 이동합니다.</p>',
            unsafe_allow_html=True,
        )

        for step in steps:
            spot = next((s for s in curated if s["name"] == step["spot_name"]), None)
            is_active = step["order"] == st.session_state.focus_order
            if render_clickable_spot_card(step, spot or {}, is_active):
                st.session_state.focus_order = step["order"]
                st.rerun()

        trip_text = meta.get("message") or meta.get("summary") or get_region_intro()
        if meta.get("map_tip"):
            trip_text += f"\n\n🗺️ {meta['map_tip']}"
        render_trip_information(trip_text[:1200])

    with right:
        center_lat, center_lng = _map_center(curated)
        route_url = build_kakao_route_url(route_for_map)
        if route_url:
            st.link_button("🗺️ 카카오맵에서 전체 동선 보기", route_url, use_container_width=True)
        render_kakao_map(
            spots=ALL_SPOTS,
            center_lat=center_lat,
            center_lng=center_lng,
            app_key=kakao_key,
            height=540,
            route_spots=route_for_map,
            show_route=len(route_for_map) > 1,
            focus_order=st.session_state.focus_order,
            focus_label=focus_label,
            title="Live Kakao Map",
        )
        st.markdown(
            '<p class="section-sub" style="margin-top:0.5rem;text-align:center;">'
            "마커 탭 · 상세 정보 · DB 좌표 기준</p>",
            unsafe_allow_html=True,
        )

    if st.button("다른 조건으로 새로 검색", use_container_width=True):
        st.session_state.screen = "home"
        st.session_state.curated_spots = []
        st.session_state.messages = []
        st.rerun()
