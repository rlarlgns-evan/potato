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
    render_screen_steps,
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

# --- session ---
if "screen" not in st.session_state:
    st.session_state.screen = "home"  # home | results

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "안녕하세요! 🥔\n\n"
                "여행 **기간·동반자·분위기**를 알려주시면 "
                "다음 화면에서 **방문 동선·카카오맵**을 보여드릴게요."
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
    st.caption("AI 후보 장소 범위")
    if not kakao_key:
        st.warning("KAKAO_MAP_APP_KEY 필요")

    st.divider()
    if st.session_state.screen == "results":
        if st.button("← 1단계: 채팅으로", use_container_width=True):
            st.session_state.screen = "home"
            st.rerun()
    elif st.session_state.curated_spots:
        if st.button("② 동선 상세 보기", type="primary", use_container_width=True):
            st.session_state.screen = "results"
            st.rerun()

candidate_spots = get_spots(region=selected_region, theme=selected_theme)
curated = st.session_state.curated_spots
meta = st.session_state.itinerary_meta
steps = st.session_state.route_steps


def _map_center(spots: list) -> tuple[float, float]:
    if spots:
        return (
            sum(s["lat"] for s in spots) / len(spots),
            sum(s["lng"] for s in spots) / len(spots),
        )
    return 37.8228, 128.1555


def _apply_curation_result(result: dict) -> None:
    st.session_state.messages.append({"role": "assistant", "content": result["message"]})
    st.session_state.curated_spots = result["curated_spots"]
    st.session_state.route_steps = result.get("route_steps", [])
    st.session_state.itinerary_meta = {
        "title": result.get("itinerary_title", ""),
        "summary": result.get("summary", ""),
        "map_tip": result.get("map_tip", ""),
        "total_duration": result.get("total_duration", ""),
    }
    if result["curated_spots"]:
        st.session_state.screen = "results"


# =============================================================================
# 화면 1 — 홈: 소개 + AI 채팅
# =============================================================================
if st.session_state.screen == "home":
    render_screen_steps(1)
    hero_header(screen=1)
    render_theme_chips()
    render_spot_carousel(candidate_spots)

    st.markdown('<div class="surface-card">', unsafe_allow_html=True)
    section_title("Plan Your Trip", "여행 취향을 말해 주세요 · AI가 코스를 설계합니다")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_prompt = st.chat_input("예: 주말 연인과 반나절, 조용한 숲길·드라이브 코스")
    st.markdown("</div>", unsafe_allow_html=True)

    if user_prompt:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.spinner("AI가 동선을 설계하는 중…"):
            result = curate_trip(
                user_message=user_prompt,
                spots=candidate_spots,
                chat_history=st.session_state.messages,
            )
        _apply_curation_result(result)
        st.rerun()

    if curated:
        st.markdown("---")
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.success(f"✅ **{meta.get('title') or '코스'}** 준비됐어요. 동선·지도를 확인해 보세요.")
        with col_b:
            if st.button("② 동선 상세 보기 →", type="primary", use_container_width=True):
                st.session_state.screen = "results"
                st.rerun()

    with st.expander("필터 후보지 전체", expanded=False):
        for spot in candidate_spots:
            st.markdown(f"- **{spot['name']}** ({spot['region']}, {spot['theme']})")

# =============================================================================
# 화면 2 — 결과: 동선 정보 + 카카오맵
# =============================================================================
else:
    if not curated:
        st.session_state.screen = "home"
        st.rerun()

    render_screen_steps(2)
    hero_header(screen=2)

    top_l, top_r = st.columns([1.2, 1])
    with top_l:
        if st.button("← 채팅 화면으로", use_container_width=False):
            st.session_state.screen = "home"
            st.rerun()

    with top_r:
        if meta.get("total_duration"):
            st.markdown(
                f'<div style="text-align:right;"><span class="stat-pill">⏱ {meta["total_duration"]}</span></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="surface-card">', unsafe_allow_html=True)
    title = meta.get("title") or "AI 추천 코스"
    st.markdown(f"### {title}")
    if meta.get("summary"):
        st.write(meta["summary"])
    st.markdown("</div>", unsafe_allow_html=True)

    route_col, map_col = st.columns([1, 1.12], gap="large")

    center_lat, center_lng = _map_center(curated)

    with route_col:
        section_title("Select Route", "방문 순서 · 티켓 카드")
        for step in steps:
            spot = next((s for s in curated if s["name"] == step["spot_name"]), None)
            render_step_ticket(step, spot)

        if meta.get("map_tip"):
            st.markdown(
                f'<div class="surface-card" style="background:#F0FDF4;border-color:#BBF7D0;">'
                f'<p style="margin:0;color:#166534;font-size:0.88rem;">🗺️ {meta["map_tip"]}</p></div>',
                unsafe_allow_html=True,
            )

        with st.expander("AI 채팅 기록", expanded=False):
            for msg in st.session_state.messages:
                role = "🧑" if msg["role"] == "user" else "🥔"
                st.markdown(f"{role} {msg['content'][:500]}")

    with map_col:
        section_title("Kakao Map", "번호 = 방문 순서 · 보라색 선 = 이동 경로")
        map_card_open("Live Route Map", "터치하여 장소 정보 확인")
        render_kakao_map(
            spots=candidate_spots,
            center_lat=center_lat,
            center_lng=center_lng,
            app_key=kakao_key,
            height=520,
            route_spots=curated,
            show_route=len(curated) > 1,
        )
        map_card_close()

    st.divider()
    if st.button("다른 조건으로 다시 Plan하기", use_container_width=True):
        st.session_state.screen = "home"
        st.rerun()
