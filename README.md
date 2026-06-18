# 샤이한 열정 감자들 · 강원 온도(ON道)

강원도 여행 AI 플래너 + KTO 6-API 데이터 + 카카오맵 동선

**배포 (유일한 런타임):** https://rlarlgns-evan.github.io/potato/

## 배포 방식

코드 변경 → `main`에 **commit & push** → GitHub Actions `Deploy GitHub Pages`가 자동 배포.

| Secret (Repository) | 용도 |
|---------------------|------|
| `KAKAO_JS_KEY` | 카카오 지도 SDK |
| `KAKAO_REST_KEY` | Kakao Directions API |
| `GOOGLE_API_KEY` | Gemini |
| `TOUR_API_SERVICE_KEY` | KTO TourAPI 동기화 (CI) |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY` | 커뮤니티·찜 (선택) |

로컬 `config.js` / `.env` / `http.server`는 **사용하지 않습니다.**

## CI 파이프라인

1. `sync_tour_all.py` (Secret 있을 때) 또는 `sync_content.py generate`
2. `sync_content.py --check` — `docs/data.js` 일치 검증
3. Secret → `docs/config.js` 생성
4. `docs/` → GitHub Pages

## 데이터 SSOT

| 경로 | 내용 |
|------|------|
| `data/spots.json`, `data/catalog.json` | UI·장소 메타 |
| `data/prompts.json` | Gemini 프롬프트·라우팅 (`TOUR_PROMPTS`) |
| `data/tour_*.json` | TourAPI fetch 결과 |
| `docs/app.js` | 프론트 (AI·Kakao 라우팅·UI) |

`python scripts/sync_content.py generate` — `data/*.json` → `docs/data.js`

## 아키텍처

| 레이어 | 경로 |
|--------|------|
| 프론트 | `docs/app.js`, `docs/data.js` |
| 프롬프트 SSOT | `data/prompts.json` |
| KTO 집계 | `kto_aggregation_service.py` |
| TourAPI | `tour_api.py`, `scripts/sync_tour_parallel_fetch.py` |

상세: `docs/TOUR_API.md`
