# TourAPI 연동 가이드 (강원 온도)

공공데이터포털에서 **동일 인증키**로 아래 API를 각각 활용신청하세요.

| API | 매뉴얼 | 용도 |
|-----|--------|------|
| 관광빅데이터 정보서비스_GW | `TourAPI_Guide_(관광빅데이터)v4.1` | 시·군 **방문자 통계** |
| 기초지자체 중심 관광지 정보서비스_GW | `TourAPI_Guide_(중심관광지)v4.1` | 시·군 **중심 관광지** 순위 |
| 관광사진갤러리 서비스_GW | `TourAPI_Guide_(관광사진)v4.2` | 지역 **관광 사진** |
| 생태관광 정보서비스_GW | `TourAPI_Guide_(생태관광)v4.2` | 시·군 **생태관광** 명소 |
| 국문 관광정보 서비스_GW | `한국관광공사_개방데이터_활용매뉴얼(국문)_v4.4` | **공식 관광지**·**축제** |

시·군구 코드: `한국관광공사_TourAPI_관광지_시군구_코드정보_v1.0.xlsx` → `data/gangwon_sigungu_codes.json`  
국문·생태 API용 **법정동·생태 시군구 코드**는 `sync_tour_ldong.py`가 API에서 조회해 같은 JSON에 병합합니다.

## 환경 변수

```env
TOUR_API_SERVICE_KEY=발급받은_인증키
TOUR_API_MOBILE_APP=GangwonOndo
```

## 한 번에 동기화

```bash
python scripts/sync_tour_all.py
```

개별 실행:

```bash
python scripts/sync_tour_ldong.py              # 법정동·생태 시군구 코드 보강
python scripts/sync_tour_stats.py --days 7    # 방문자 통계
python scripts/sync_tour_hub.py               # 중심 관광지
python scripts/sync_tour_photos.py            # 관광 사진
python scripts/sync_tour_kor.py               # 국문 관광지 + 축제
python scripts/sync_tour_eco.py               # 생태관광
python scripts/sync_content.py generate       # docs/data.js 반영
```

엑셀에서 시군구 코드 재가져오기:

```bash
pip install openpyxl
python scripts/import_sigungu_codes.py
```

## 생성되는 데이터

| 파일 | API | UI 반영 |
|------|-----|---------|
| `data/tour_visitor_stats.json` | DataLab `locgoRegnVisitrDDList` | 지도 툴팁 **방문** |
| `data/tour_hub_spots.json` | `LocgoHubTarService1/areaBasedList1` | 지도 툴팁 **중심 관광지** |
| `data/tour_region_photos.json` | `PhotoGalleryService1/gallerySearchList1` | 툴팁 사진·관광지 카드 썸네일 |
| `data/tour_kor_spots.json` | `KorService2/areaBasedList2` | 툴팁 **공식 관광지**·카드 썸네일 |
| `data/tour_kor_festivals.json` | `KorService2/searchFestival2` | 툴팁·축제 탭 (큐레이션과 병합) |
| `data/tour_eco_spots.json` | `GreenTourService1/areaBasedList1` | 지도 툴팁 **생태관광** |
| `data/gangwon_sigungu_codes.json` | 엑셀 + `ldongCode2` + `areaCode1` | API 요청용 코드 |

## API 상세

### 생태관광 `areaBasedList1`

```
GET http://apis.data.go.kr/B551011/GreenTourService1/areaBasedList1
  ?serviceKey=...&areaCode=32&sigunguCode=1
  &numOfRows=10&pageNo=1&MobileOS=ETC&MobileApp=GangwonOndo&_type=json
```

- 강원 `areaCode=32` (GreenTour 전용 지역코드, Hub API의 51과 다름)
- `sigunguCode`는 `areaCode1?areaCode=32`로 조회

응답: `title`, `summary`, `mainimage`, `addr`, `tel`, `contentId` …

### 국문 관광지 `areaBasedList2`

```
GET http://apis.data.go.kr/B551011/KorService2/areaBasedList2
  ?serviceKey=...&lDongRegnCd=51&lDongSignguCd=110&contentTypeId=12
  &arrange=O&numOfRows=10&pageNo=1&MobileOS=ETC&MobileApp=GangwonOndo&_type=json
```

- `lDongRegnCd` / `lDongSignguCd`: `ldongCode2` 법정동 코드 (Hub `areaCd`와 별도)

### 국문 축제 `searchFestival2`

```
GET http://apis.data.go.kr/B551011/KorService2/searchFestival2
  ?serviceKey=...&lDongRegnCd=51&lDongSignguCd=820
  &eventStartDate=20260101&eventEndDate=20261231&arrange=O&_type=json
```

### 중심관광지 `areaBasedList1`

```
GET http://apis.data.go.kr/B551011/LocgoHubTarService1/areaBasedList1
  ?serviceKey=...&baseYm=202504&areaCd=51&signguCd=51150
  &numOfRows=10&pageNo=1&MobileOS=ETC&MobileApp=GangwonOndo&_type=json
```

응답: `hubTatsNm`, `hubRank`, `hubCtgryMclsNm`, `mapX`, `mapY` …

### 관광사진 `gallerySearchList1`

```
GET http://apis.data.go.kr/B551011/PhotoGalleryService1/gallerySearchList1
  ?serviceKey=...&keyword=강원+강릉시+관광&arrange=C
  &numOfRows=2&pageNo=1&MobileOS=ETC&MobileApp=GangwonOndo&_type=json
```

응답: `galTitle`, `galWebImageUrl`, `galPhotographyLocation` …

## GitHub Pages

Repository Secret `TOUR_API_SERVICE_KEY` 설정 시 배포 workflow가 자동 동기화합니다.

## 보안

인증키는 브라우저에 노출하지 마세요. 빌드/로컬 스크립트에서만 사용합니다.
