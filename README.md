# 샤이한 열정 감자들

강원도 인구 감소 지역의 숨은 여행지를 **카카오맵**과 AI 챗봇으로 추천하는 Streamlit 서비스입니다.

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 카카오 지도 API 키 설정

1. [카카오 개발자](https://developers.kakao.com) → 앱 생성
2. **앱 설정 → 플랫폼 키**에서 **JavaScript 키** 확인
3. **JavaScript SDK 도메인** 등록:
   - 로컬: `http://localhost:8501`
   - Streamlit Cloud: `https://본인앱이름.streamlit.app`
4. `.env` 또는 Streamlit Secrets에 추가:

```env
KAKAO_MAP_APP_KEY=발급받은_JavaScript_키
```

## Streamlit Cloud Secrets

[share.streamlit.io](https://share.streamlit.io) → 앱 **Settings** → **Secrets**에 `secrets.example.toml` 형식으로 붙여넣기.

```toml
AI_PROVIDER = "google"

GOOGLE_API_KEY = "your-gemini-api-key"
GOOGLE_MODEL = "gemini-2.5-flash"

KAKAO_MAP_APP_KEY = "your-kakao-javascript-key"

OPENAI_API_KEY = ""
OPENAI_MODEL = "gpt-4o-mini"
```

저장 후 **Reboot app** 실행.
