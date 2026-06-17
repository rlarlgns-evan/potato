# 샤이한 열정 감자들 · 강원 온도(ON道)

강원도 여행 AI 플래너 + KTO 6-API 데이터 + 카카오맵 동선 (GitHub Pages)

**배포:** https://rlarlgns-evan.github.io/potato/

## 로컬 실행

```bash
# 정적 사이트 (docs/)
python -m http.server 8080 --directory docs
# 브라우저: http://localhost:8080
# docs/config.js ← docs/config.example.js 복사 후 API 키 설정
```

## Python (KTO 동기화·큐레이션 백엔드)

```bash
pip install -r requirements.txt
python scripts/sync_tour_all.py          # 6 KTO API 병렬 fetch + data.js 생성
python scripts/sync_content.py generate  # data/*.json → docs/data.js
```

## 환경 변수 (`.env`)

```env
AI_PROVIDER=google
GOOGLE_API_KEY=
GOOGLE_MODEL=gemini-3.5-flash
KAKAO_MAP_APP_KEY=   # 카카오 JavaScript 키
TOUR_API_SERVICE_KEY=
```

### 카카오 지도

1. [developers.kakao.com](https://developers.kakao.com) → JavaScript 키
2. **JavaScript SDK 도메인:** `http://localhost:8080`, `https://rlarlgns-evan.github.io`

## 아키텍처

| 레이어 | 경로 |
|--------|------|
| 프론트 | `docs/app.js`, `docs/data.js` |
| KTO 집계 | `kto_aggregation_service.py` |
| 프롬프트 SSOT | `data/prompts.json` → `TOUR_PROMPTS` |
| 큐레이션 | `services/curation/`, `chatbot.py` |
| TourAPI | `tour_api.py`, `scripts/sync_tour_*.py` |

## TourAPI

- 6 API 병렬 동기화: `scripts/sync_tour_parallel_fetch.py`
- 가이드: `docs/TOUR_API.md`
