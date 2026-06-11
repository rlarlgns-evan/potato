import config  # noqa: F401 — .env 로드

import os

import streamlit as st

from chatbot import curate_trip
from database import get_all_spots, init_db
from kakao_map import (
    build_kakao_route_url,
    build_route_markers,
    get_kakao_app_key,
    render_kakao_map,
)
from ui import (
    inject_styles,
    render_course_cards_list,
    render_planner_map_chrome,
    render_tailored_header,
    render_trip_plan_panel,
    render_voyage_app_sidebar,
    render_voyage_explore_page,
    render_voyage_top_nav,
)

st.set_page_config(
    page_title="VoyageAI · 강원",
    page_icon="✦",
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
        "source": result.get("source", "local"),
        "trip_intent": result.get("trip_intent") or {},
        "transit_plan": result.get("transit_plan") or {},
        "accommodation": result.get("accommodation") or {},
        "day_plans": result.get("day_plans") or [],
    }
    st.session_state.focus_order = 1
    if result["curated_spots"]:
        st.session_state.screen = "results"


@st.cache_data(ttl=86400 * 7, show_spinner=False)
def _cached_curation(prompt: str, provider: str) -> dict:
    """같은 질문은 7일 캐시 → AI(API) 호출 최소화."""
    return curate_trip(user_message=prompt, spots=ALL_SPOTS, chat_history=[])


def _run_curation(user_prompt: str) -> None:
    provider = os.getenv("AI_PROVIDER", "openai").lower()
    st.session_state.messages = [{"role": "user", "content": user_prompt}]
    with st.spinner("맞춤 동선 설계 중…"):
        result = _cached_curation(user_prompt, provider)
    st.session_state.messages.append(
        {"role": "assistant", "content": result["message"]}
    )
    _apply_curation_result(result, user_prompt)
    src = result.get("source", "")
    if src == "ai_required_fail":
        st.session_state._toast = result.get("message", "AI 일정을 만들지 못했어요.")
    elif src in ("local_skip", "local_api_fail", "local"):
        from curation_sources import source_label
        st.session_state._toast = f"{source_label(src)} · {result.get('itinerary_title', '코스')}"
    elif not result.get("curated_spots"):
        st.session_state._toast = "조건에 맞는 코스를 찾지 못했어요. 다르게 표현해 보세요."


def _handle_query_actions() -> None:
    """상단 탭·사이드바·추천 칩·관심사 토글 → 쿼리 파라미터 라우팅."""
    qp = st.query_params

    nav = qp.get("nav")
    if nav:
        del qp["nav"]
        if nav == "explore":
            st.session_state.screen = "home"
        elif nav == "planner":
            if st.session_state.curated_spots:
                st.session_state.screen = "results"
            else:
                st.session_state.screen = "home"
                st.session_state._toast = "Planner는 AI 코스를 먼저 만들면 열려요."
        else:
            st.session_state._toast = "🚧 곧 제공될 기능이에요."
        st.rerun()

    sb = qp.get("sb")
    if sb:
        del qp["sb"]
        if sb in ("dashboard", "destinations"):
            st.session_state.screen = "home"
        elif sb == "itinerary":
            st.session_state.screen = (
                "results" if st.session_state.curated_spots else "home"
            )
            if not st.session_state.curated_spots:
                st.session_state._toast = "아직 생성된 일정이 없어요."
        elif sb == "favorites":
            st.session_state._toast = "♡ 즐겨찾기는 준비 중이에요."
        elif sb == "logout":
            for key in (
                "screen", "messages", "curated_spots", "route_steps",
                "itinerary_meta", "focus_order", "last_user_query",
                "show_all_interests",
            ):
                st.session_state.pop(key, None)
            st.session_state.screen = "home"
            st.session_state._toast = "로그아웃했어요."
        st.rerun()

    interests = qp.get("interests")
    if interests is not None:
        del qp["interests"]
        st.session_state.show_all_interests = interests == "all"
        st.rerun()

    ask = qp.get("ask")
    if ask:
        del qp["ask"]
        prompt = ask.strip()
        if prompt:
            _run_curation(prompt)
        st.rerun()


_handle_query_actions()

if st.session_state.get("_toast"):
    st.toast(st.session_state.pop("_toast"))


# =============================================================================
# ① Explore — AI 채팅 · 강원 컨텍스트
# =============================================================================
if st.session_state.screen == "home":
    render_voyage_explore_page(len(ALL_SPOTS))

    from content_loader import load_suggestions

    welcome = (
        "✦ 안녕하세요! 강원도 여행의 무엇이든 물어보세요.\n\n"
        "출발지·교통·일정·동행·테마를 알려주시면 맞춤 동선과 지도를 만들어 드릴게요."
    )
    suggestions = load_suggestions()[:4]

    with st.container(border=True):
        st.caption("● AI Concierge · 실시간 여행 추천")
        if not st.session_state.messages:
            with st.chat_message("assistant", avatar="✦"):
                st.markdown(welcome)
            st.markdown(
                '<p style="margin:0.5rem 0 0.35rem;font-size:0.68rem;font-weight:700;'
                'letter-spacing:0.06em;text-transform:uppercase;color:#3e4947;">'
                "이렇게 물어보세요</p>",
                unsafe_allow_html=True,
            )
            pill_cols = st.columns(min(len(suggestions), 4))
            for i, s in enumerate(suggestions):
                with pill_cols[i % len(pill_cols)]:
                    if st.button(s["label"], key=f"agent_pill_{i}", use_container_width=True):
                        _run_curation(s["prompt"])
                        st.rerun()
        else:
            for msg in st.session_state.messages:
                with st.chat_message(
                    msg["role"],
                    avatar="✦" if msg["role"] == "assistant" else None,
                ):
                    st.markdown(msg["content"])

    if user_prompt := st.chat_input(
        "출발지, 교통, 일정, 동행, 테마를 자유롭게 입력하세요…",
        key="agent_chat_input",
    ):
        _run_curation(user_prompt.strip())
        st.rerun()

# =============================================================================
# ② Planner — Tailored for You · 카드 + 지도
# =============================================================================
else:
    curated = st.session_state.curated_spots
    if not curated:
        st.session_state.screen = "home"
        st.rerun()

    meta = st.session_state.itinerary_meta
    steps = st.session_state.route_steps
    focus_order = int(st.session_state.focus_order or 1)

    if st.query_params.get("focus"):
        try:
            focus_order = int(st.query_params["focus"])
            st.session_state.focus_order = focus_order
        except (ValueError, TypeError):
            pass

    render_voyage_top_nav("planner")

    sb_col, main_col = st.columns([0.16, 0.84], gap="small")
    with sb_col:
        render_voyage_app_sidebar("itinerary")
        if st.button("← 홈으로", use_container_width=True):
            st.session_state.screen = "home"
            st.rerun()

    with main_col:
        render_tailored_header(meta, st.session_state.last_user_query, len(steps))
        render_trip_plan_panel(meta)

        route_for_map = build_route_markers(curated, steps)
        list_col, map_col = st.columns([1, 1.08], gap="medium")

        with list_col:
            focus_order = render_course_cards_list(steps, curated, focus_order)

        focus_spot = next(
            (m for m in route_for_map if m["order"] == focus_order),
            route_for_map[0] if route_for_map else None,
        )
        focus_label = (
            f"{focus_spot['name']}" if focus_spot else ""
        )
        query_chip = st.session_state.last_user_query[:40] + (
            "…" if len(st.session_state.last_user_query) > 40 else ""
        )

        with map_col:
            render_planner_map_chrome(query_chip, focus_label)
            center_lat, center_lng = _map_center(curated)
            if focus_spot:
                center_lat, center_lng = float(focus_spot["lat"]), float(focus_spot["lng"])
            route_url = build_kakao_route_url(route_for_map)
            if route_url:
                st.link_button(
                    "🧭 카카오맵에서 길찾기", route_url, use_container_width=True
                )
            render_kakao_map(
                spots=ALL_SPOTS,
                center_lat=center_lat,
                center_lng=center_lng,
                app_key=kakao_key,
                height=520,
                route_spots=route_for_map,
                show_route=len(route_for_map) > 1,
                focus_order=focus_order,
                focus_label=focus_label,
                title="",
            )

        st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
        new_col, _spacer = st.columns([1, 2])
        with new_col:
            if st.button("✦ 새 여행 설계하기", type="primary", use_container_width=True):
                st.session_state.screen = "home"
                st.session_state.curated_spots = []
                st.session_state.messages = []
                st.session_state.last_user_query = ""
                st.rerun()
