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
            "content": "안녕하세요! 원하는 여행 분위기를 알려주시면 AI가 코스를 짜고, 지도에 동선을 보여드릴게요.",
        }
    ]
if "curated_spots" not in st.session_state:
    st.session_state.curated_spots = []
if "map_tip" not in st.session_state:
    st.session_state.map_tip = ""

st.title("샤이한 열정 감자들")
st.caption("프롬프트 입력 → AI 큐레이션 → 카카오맵 동선 안내")

kakao_key = get_kakao_app_key()

with st.sidebar:
    st.subheader("여행 필터")
    regions, themes = get_filter_options()
    selected_region = st.selectbox("지역", ["전체"] + regions)
    selected_theme = st.selectbox("테마", ["전체"] + themes)
    st.info("필터는 AI가 고를 **후보 장소** 범위를 정합니다.")
    if not kakao_key:
        st.warning("`.env` 또는 Secrets에 `KAKAO_MAP_APP_KEY`를 넣어 주세요.")

candidate_spots = get_spots(region=selected_region, theme=selected_theme)

# 1) 프롬프트 입력 (AI)
st.subheader("1. AI에게 여행 취향 알려주기")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_prompt = st.chat_input("예: 이번 주말, 조용한 숲길 위주로 반나절 코스 추천해줘")
if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.spinner("AI가 코스를 분석하는 중..."):
        result = curate_trip(
            user_message=user_prompt,
            spots=candidate_spots,
            chat_history=st.session_state.messages,
        )
    st.session_state.messages.append({"role": "assistant", "content": result["message"]})
    st.session_state.curated_spots = result["curated_spots"]
    st.session_state.map_tip = result.get("map_tip", "")
    st.rerun()

curated = st.session_state.curated_spots
map_spots = curated if curated else candidate_spots

if map_spots:
    center_lat = sum(s["lat"] for s in map_spots) / len(map_spots)
    center_lng = sum(s["lng"] for s in map_spots) / len(map_spots)
else:
    center_lat, center_lng = 37.8228, 128.1555

st.divider()
st.subheader("2. AI 추천 결과")

if curated:
    if st.session_state.map_tip:
        st.success(st.session_state.map_tip)
    for idx, spot in enumerate(curated, start=1):
        map_url = f"https://map.kakao.com/link/map/{spot['name']},{spot['lat']},{spot['lng']}"
        st.markdown(
            f"**{idx}. {spot['name']}** ({spot['region']} · {spot['theme']})  \n"
            f"{spot['description']}  \n"
            f"[카카오맵에서 보기]({map_url})"
        )
else:
    st.info("채팅 입력 전에는 아래 지도에 **필터 후보지**가 표시됩니다. AI 추천 후 동선이 갱신됩니다.")

st.divider()
st.subheader("3. 카카오맵")

if curated:
    st.caption("AI 추천 코스 (번호 마커 · 주황 동선)")
    render_kakao_map(
        spots=candidate_spots,
        center_lat=center_lat,
        center_lng=center_lng,
        app_key=kakao_key,
        height=480,
        route_spots=curated,
        show_route=len(curated) > 1,
    )
else:
    st.caption("현재 필터의 후보 여행지")
    render_kakao_map(
        spots=candidate_spots,
        center_lat=center_lat,
        center_lng=center_lng,
        app_key=kakao_key,
        height=480,
    )

with st.expander("필터 조건의 전체 후보지 보기"):
    if not candidate_spots:
        st.warning("조건에 맞는 여행지가 없어요. 필터를 조정해 보세요.")
    else:
        for spot in candidate_spots:
            st.markdown(f"- **{spot['name']}** ({spot['region']}, {spot['theme']})")
