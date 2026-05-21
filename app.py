import streamlit as st

from chatbot import generate_reply
from database import get_filter_options, get_spots, init_db
from kakao_map import get_kakao_app_key, render_kakao_map

st.set_page_config(page_title="샤이한 열정 감자들", page_icon="🥔", layout="wide")

init_db()

st.title("샤이한 열정 감자들")
st.caption("강원도 인구 감소 지역 숨은 여행지 추천 서비스")

with st.sidebar:
    st.subheader("여행 필터")
    regions, themes = get_filter_options()
    selected_region = st.selectbox("지역", ["전체"] + regions)
    selected_theme = st.selectbox("테마", ["전체"] + themes)
    st.info("AI 키가 없으면 로컬 추천 로직으로 자동 동작합니다.")
    if not get_kakao_app_key():
        st.warning("카카오 지도 키(`KAKAO_MAP_APP_KEY`)를 설정하면 지도가 표시됩니다.")

spots = get_spots(region=selected_region, theme=selected_theme)

left_col, right_col = st.columns([1.25, 1], gap="large")

with left_col:
    st.subheader("지도에서 보기")
    if spots:
        center_lat = sum(spot["lat"] for spot in spots) / len(spots)
        center_lng = sum(spot["lng"] for spot in spots) / len(spots)
    else:
        center_lat, center_lng = 37.8228, 128.1555

    render_kakao_map(
        spots=spots,
        center_lat=center_lat,
        center_lng=center_lng,
        app_key=get_kakao_app_key(),
        height=500,
    )

    st.subheader("추천 후보")
    if not spots:
        st.warning("조건에 맞는 여행지가 없어요. 필터를 조정해 보세요.")
    else:
        for spot in spots:
            map_url = (
                f"https://map.kakao.com/link/map/"
                f"{spot['name']},{spot['lat']},{spot['lng']}"
            )
            st.markdown(
                f"**{spot['name']}**  \n"
                f"- 지역: {spot['region']}  \n"
                f"- 테마: {spot['theme']}  \n"
                f"- 설명: {spot['description']}  \n"
                f"- [카카오맵에서 보기]({map_url})"
            )

with right_col:
    st.subheader("AI 로컬 큐레이터")
    st.caption("취향/예산/동반자/이동수단을 함께 알려주면 더 정확해져요.")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "안녕하세요! 어떤 분위기의 강원도 여행을 찾고 계신가요?",
            }
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_prompt = st.chat_input("예: 이번 주말, 조용한 숲길 위주로 반나절 코스 추천해줘")
    if user_prompt:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.write(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("코스를 큐레이션 중..."):
                reply = generate_reply(
                    user_message=user_prompt,
                    spots=spots,
                    chat_history=st.session_state.messages,
                )
                st.write(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})
