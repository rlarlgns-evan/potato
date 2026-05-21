import config  # noqa: F401 — .env 로드

import streamlit as st

from chatbot import curate_trip
from database import get_filter_options, get_spots, init_db
from kakao_map import get_kakao_app_key, render_kakao_map

st.set_page_config(page_title="샤이한 열정 감자들", page_icon="🥔", layout="wide")

init_db()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "안녕하세요! 🥔\n\n"
                "여행 **기간·동반자·분위기**(예: 반나절, 조용한 숲길)를 알려주시면 "
                "AI가 **방문 순서가 있는 동선**을 짜고, 바로 아래 **카카오맵**에 표시해 드려요."
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

st.title("샤이한 열정 감자들")
st.caption("① 취향 입력 → ② AI 동선 추천 → ③ 카카오맵에서 확인")

with st.sidebar:
    st.subheader("여행 필터")
    regions, themes = get_filter_options()
    selected_region = st.selectbox("지역", ["전체"] + regions)
    selected_theme = st.selectbox("테마", ["전체"] + themes)
    st.info("필터 = AI가 고를 **후보 장소** 범위")
    if not kakao_key:
        st.warning("`KAKAO_MAP_APP_KEY` 설정 필요")

candidate_spots = get_spots(region=selected_region, theme=selected_theme)

# --- 1. 채팅 ---
st.subheader("1️⃣ 여행 취향 말하기")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_prompt = st.chat_input("예: 이번 주말 연인과 반나절, 힐링·드라이브 위주로 코스 짜줘")
if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.spinner("AI가 방문 순서·동선을 설계하는 중..."):
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

st.divider()

# --- 2 + 3. 동선 카드 + 지도 (나란히) ---
if curated:
    st.subheader("2️⃣ AI 추천 여행 동선")
    if meta.get("title"):
        st.markdown(f"### {meta['title']}")
    if meta.get("summary"):
        st.write(meta["summary"])
    if meta.get("total_duration"):
        st.metric("예상 일정", meta["total_duration"])

    route_col, map_col = st.columns([1, 1.15], gap="large")

    with route_col:
        for step in steps:
            stay = step.get("stay_minutes")
            stay_label = f" · 약 {stay}분" if stay else ""
            with st.container(border=True):
                st.markdown(f"#### {step['order']}. {step['spot_name']}")
                st.caption(f"{step.get('region', '')} · {step.get('theme', '')}{stay_label}")
                st.write(step.get("why", ""))
                if step.get("move_to_next"):
                    st.info(f"🚗 다음 이동: {step['move_to_next']}")
                spot = next((s for s in curated if s["name"] == step["spot_name"]), None)
                if spot:
                    url = f"https://map.kakao.com/link/map/{spot['name']},{spot['lat']},{spot['lng']}"
                    st.link_button(f"📍 {step['spot_name']} 카카오맵", url, use_container_width=True)

        if meta.get("map_tip"):
            st.success(meta["map_tip"])

    with map_col:
        st.markdown("### 3️⃣ 카카오맵 동선")
        st.caption("번호 = 방문 순서 · 주황선 = 이동 경로")
        render_kakao_map(
            spots=candidate_spots,
            center_lat=center_lat,
            center_lng=center_lng,
            app_key=kakao_key,
            height=520,
            route_spots=curated,
            show_route=len(curated) > 1,
        )
else:
    st.subheader("2️⃣ 카카오맵 (후보지)")
    st.info("👆 채팅으로 취향을 입력하면 **방문 순서·이동 팁·지도 동선**이 한 번에 갱신됩니다.")
    render_kakao_map(
        spots=candidate_spots,
        center_lat=center_lat,
        center_lng=center_lng,
        app_key=kakao_key,
        height=480,
    )

with st.expander("필터 후보지 전체"):
    for spot in candidate_spots:
        st.markdown(f"- **{spot['name']}** ({spot['region']}, {spot['theme']})")
