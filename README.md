# 샤이한 열정 감자들 · 강원 온도(ON道)

강원도 여행 AI 플래너 + KTO 6-API 데이터 + 카카오맵 동선 (GitHub Pages)

**배포:** https://rlarlgns-evan.github.io/potato/

## 로컬 실행

```bash
# 정적 사이트 (docs/) — UI 확인용 (API 키는 GitHub Pages 배포에서만 주입)
python -m http.server 8080 --directory docs
# 브라우저: http://localhost:8080
```

API 키(`KAKAO_JS_KEY`, `KAKAO_REST_KEY`, `GOOGLE_API_KEY` 등)는 **저장소·로컬 파일에 두지 않습니다.**  
배포 시 GitHub Actions Secret → `docs/config.js` 자동 생성.

## Python (KTO 데이터 동기화)

```bash
pip install -r requirements.txt
python scripts/sync_tour_all.py          # 6 KTO API 병렬 fetch
python scripts/sync_content.py generate  # data/*.json → docs/data.js
```

## 환경 변수 (`.env`)

TourAPI 동기화용 — `.env.example` 참고.

```env
TOUR_API_SERVICE_KEY=
TOUR_API_MOBILE_APP=GangwonOndo
```

## 아키텍처

| 레이어 | 경로 |
|--------|------|
| 프론트 (AI·라우팅·UI) | `docs/app.js`, `docs/data.js` |
| 프롬프트·라우팅 SSOT | `data/prompts.json` → `TOUR_PROMPTS` |
| KTO 집계 | `kto_aggregation_service.py` |
| TourAPI | `tour_api.py`, `scripts/sync_tour_parallel_fetch.py` |

## TourAPI

- 6 API 병렬 동기화: `scripts/sync_tour_all.py` (내부: `sync_tour_parallel_fetch.py`)
- 가이드: `docs/TOUR_API.md`
