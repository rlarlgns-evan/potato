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

## 환경 변수 (`.env` / Streamlit Secrets)

```env
AI_PROVIDER=google
GOOGLE_API_KEY=
GOOGLE_MODEL=gemini-3.5-flash
KAKAO_MAP_APP_KEY=   # 카카오 JavaScript 키 (REST API 키 아님)
```

### 카카오 지도 (MY TRIP)

1. [developers.kakao.com](https://developers.kakao.com) → 앱 → **플랫폼 키** → **JavaScript 키** 복사  
2. **JavaScript SDK 도메인** 등록:
   - `https://kangwon-potato.streamlit.app` (배포 앱)
   - `http://localhost:8501` (로컬 실행)
3. Streamlit Cloud → **Settings → Secrets**에 `KAKAO_MAP_APP_KEY` 추가 후 **Reboot app**

카카오 로그인 Redirect URI는 지도만 쓸 때 **비워도 됩니다**.

## 추후 연동

- `tour_api.py` — 한국관광공사 **관광빅데이터(DataLab)** 방문자 통계 (`locgoRegnVisitrDDList`, `metcoRegnVisitrDDList`)
- `scripts/sync_tour_stats.py` — 강원 시·군 방문자 데이터 → `data/tour_visitor_stats.json` → 지도 툴팁
- `gangwon_content.py` — 날씨·축제 (Open-Meteo + 로컬 카탈로그)
- `database.py` — API 기반 관광지 동기화 (`INSERT OR IGNORE` 구조 준비됨)

### TourAPI 관광빅데이터 설정

1. [공공데이터포털](https://www.data.go.kr/data/15101972/openapi.do)에서 **한국관광공사_관광빅데이터 정보서비스_GW** 활용신청
2. `.env`에 `TOUR_API_SERVICE_KEY` 추가
3. `python scripts/sync_tour_stats.py` → `python scripts/sync_content.py generate`
4. (선택) GitHub Actions Secret `TOUR_API_SERVICE_KEY` — 배포 시 자동 동기화

> 관광지 목록·상세·축제 일정은 **국문 관광정보 서비스**(KorService2) API가 별도입니다. 매뉴얼: `TourAPI_Guide_(국문)v4.4.zip`

## AI 관광지 범위

필터와 무관하게 **강원도 전역** DB 관광지(`get_all_spots()`)에서 AI가 선택합니다.
