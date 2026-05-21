# 샤이한 열정 감자들

강원도 여행 AI 플래너 + 카카오맵 동선 (Streamlit)

## 화면 흐름

1. **홈** — 강원도 날씨·축제·하이라이트 + **AI 검색창**
2. **MY TRIP** — AI가 고른 관광지 동선 · 인터랙티브 카드 · 카카오맵

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 환경 변수 (`.env`)

```env
AI_PROVIDER=google
GOOGLE_API_KEY=
GOOGLE_MODEL=gemini-2.5-flash
KAKAO_MAP_APP_KEY=
```

## 추후 연동

- `gangwon_content.py` — 한국관광공사 Tour API (날씨·축제·관광지)
- `database.py` — API 기반 관광지 동기화 (`INSERT OR IGNORE` 구조 준비됨)

## AI 관광지 범위

필터와 무관하게 **강원도 전역** DB 관광지(`get_all_spots()`)에서 AI가 선택합니다.
