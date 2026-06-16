"""
한국관광공사 TourAPI 클라이언트 (강원 온도 연동).

매뉴얼
- 관광빅데이터 v4.1 → DataLabService
- 기초지자체 중심관광지 v4.1 → LocgoHubTarService1
- 관광지별 연관관광지 v4.1 → TarRlteTarService1
- 관광사진 v4.2 → PhotoGalleryService1
- 생태관광 v4.2 → GreenTourService1
- 국문 관광정보 v4.4 → KorService2
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SIGUNGU_CODES_PATH = ROOT / "data" / "gangwon_sigungu_codes.json"

DATALAB_BASE = "http://apis.data.go.kr/B551011/DataLabService"
HUB_BASE = "http://apis.data.go.kr/B551011/LocgoHubTarService1"
RELATE_BASE = "http://apis.data.go.kr/B551011/TarRlteTarService1"
PHOTO_BASE = "http://apis.data.go.kr/B551011/PhotoGalleryService1"
ECO_BASE = "http://apis.data.go.kr/B551011/GreenTourService1"
KOR_BASE = "http://apis.data.go.kr/B551011/KorService2"

MOBILE_APP = os.getenv("TOUR_API_MOBILE_APP", "GangwonOndo")
GANGWON_AREA_CD = 51
ECO_GANGWON_AREA_CODE = 32  # GreenTourService1 지역코드 (구 강원도)
KOR_CONTENT_TYPE_ATTRACTION = "12"
KOR_CONTENT_TYPE_FESTIVAL = "15"

GANGWON_REGIONS: tuple[str, ...] = (
    "강릉시",
    "고성군",
    "동해시",
    "삼척시",
    "속초시",
    "양구군",
    "양양군",
    "영월군",
    "원주시",
    "인제군",
    "정선군",
    "철원군",
    "춘천시",
    "태백시",
    "홍천군",
    "화천군",
    "횡성군",
    "평창군",
)

TOU_DIV_LABELS = {
    "1": "local",
    "2": "outsider",
    "3": "foreign",
}


class TourApiError(RuntimeError):
    pass


def get_service_key() -> str:
    key = os.getenv("TOUR_API_SERVICE_KEY") or os.getenv("DATA_GO_KR_SERVICE_KEY", "")
    if not key.strip():
        raise TourApiError(
            "TOUR_API_SERVICE_KEY가 없습니다. 공공데이터포털에서 아래 API 활용신청 후 .env에 키를 넣으세요.\n"
            "- 관광빅데이터 정보서비스_GW\n"
            "- 기초지자체 중심 관광지 정보서비스_GW\n"
            "- 관광지별 연관관광지 정보서비스_GW\n"
            "- 관광사진갤러리 서비스_GW\n"
            "- 생태관광 정보서비스_GW\n"
            "- 국문 관광정보 서비스_GW"
        )
    return key.strip()


def load_gangwon_sigungu_codes() -> dict[str, Any]:
    if not SIGUNGU_CODES_PATH.exists():
        raise TourApiError(f"시군구 코드 파일이 없습니다: {SIGUNGU_CODES_PATH}")
    return json.loads(SIGUNGU_CODES_PATH.read_text(encoding="utf-8"))


def save_gangwon_sigungu_codes(data: dict[str, Any]) -> None:
    SIGUNGU_CODES_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _parse_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = (payload.get("response") or {}).get("body") or {}
    items = body.get("items") or {}
    raw = items.get("item")
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [raw]
    return list(raw)


def _check_header(payload: dict[str, Any]) -> None:
    header = (payload.get("response") or {}).get("header") or {}
    code = str(header.get("resultCode", ""))
    if code and code not in ("0000", "00"):
        raise TourApiError(f"TourAPI {code}: {header.get('resultMsg', 'unknown')}")


def _call_tour_api(
    base_url: str,
    operation: str,
    extra: dict[str, Any],
    *,
    service_key: str | None = None,
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    key = service_key or get_service_key()
    params: dict[str, Any] = {
        "serviceKey": key,
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "MobileOS": "ETC",
        "MobileApp": MOBILE_APP,
        "_type": "json",
        **extra,
    }
    url = f"{base_url}/{operation}?{urlencode(params)}"
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise TourApiError(f"HTTP {exc.code}: {operation}") from exc
    except (URLError, json.JSONDecodeError) as exc:
        raise TourApiError(f"요청 실패: {operation}") from exc

    _check_header(data)
    return data


def _fetch_all_pages(
    base_url: str,
    operation: str,
    extra: dict[str, Any],
    *,
    service_key: str | None = None,
    num_of_rows: int = 100,
    max_pages: int = 20,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        payload = _call_tour_api(
            base_url,
            operation,
            extra,
            service_key=service_key,
            page_no=page,
            num_of_rows=num_of_rows,
        )
        batch = _parse_items(payload)
        if not batch:
            break
        out.extend(batch)
        body = (payload.get("response") or {}).get("body") or {}
        total = int(body.get("totalCount") or 0)
        if len(out) >= total or len(batch) < num_of_rows:
            break
    return out


def _default_base_ym() -> str:
    """중심관광지 API 기준연월 — 전월."""
    first = date.today().replace(day=1)
    prev = first - timedelta(days=1)
    return prev.strftime("%Y%m")


def _fmt_ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _fmt_count(n: float) -> str:
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}억"
    if n >= 10_000:
        return f"{n / 10_000:.1f}만"
    if n >= 1_000:
        return f"{n / 1_000:.1f}천"
    return str(int(round(n)))


def _normalize_region_name(name: str) -> str:
    return (name or "").strip().replace(" ", "")


def _match_gangwon_region(signgu_nm: str) -> str | None:
    norm = _normalize_region_name(signgu_nm)
    for region in GANGWON_REGIONS:
        if norm == _normalize_region_name(region):
            return region
        base = region.rstrip("시군")
        if norm == base or norm.startswith(base):
            return region
    return None


def _clean_hub_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").replace("/", " · ").strip())


def _parse_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------- DataLab (관광빅데이터) ----------


def call_datalab(
    operation: str,
    *,
    start_ymd: str,
    end_ymd: str,
    page_no: int = 1,
    num_of_rows: int = 1000,
    service_key: str | None = None,
) -> dict[str, Any]:
    return _call_tour_api(
        DATALAB_BASE,
        operation,
        {"startYmd": start_ymd, "endYmd": end_ymd},
        service_key=service_key,
        page_no=page_no,
        num_of_rows=num_of_rows,
    )


def fetch_datalab_items(
    operation: str,
    *,
    start_ymd: str,
    end_ymd: str,
    service_key: str | None = None,
) -> list[dict[str, Any]]:
    return _fetch_all_pages(
        DATALAB_BASE,
        operation,
        {"startYmd": start_ymd, "endYmd": end_ymd},
        service_key=service_key,
        num_of_rows=1000,
        max_pages=50,
    )


def aggregate_locgo_visitors(items: list[dict[str, Any]], *, days: int) -> dict[str, Any]:
    buckets: dict[str, dict[str, float]] = {}

    for item in items:
        region = _match_gangwon_region(str(item.get("signguNm") or ""))
        if not region:
            continue
        div = TOU_DIV_LABELS.get(str(item.get("touDivCd") or ""), "other")
        try:
            num = float(item.get("touNum") or 0)
        except (TypeError, ValueError):
            num = 0.0
        slot = buckets.setdefault(region, {"local": 0.0, "outsider": 0.0, "foreign": 0.0, "other": 0.0})
        slot[div] = slot.get(div, 0.0) + num

    regions: dict[str, Any] = {}
    for region, counts in buckets.items():
        local = counts["local"]
        outsider = counts["outsider"]
        foreign = counts["foreign"]
        total = local + outsider + foreign + counts.get("other", 0.0)
        if total <= 0:
            continue
        outsider_pct = round(outsider / total * 100)
        foreign_pct = round(foreign / total * 100)
        avg_daily = total / max(days, 1)
        regions[region] = {
            "total": int(round(total)),
            "avg_daily": int(round(avg_daily)),
            "local": int(round(local)),
            "outsider": int(round(outsider)),
            "foreign": int(round(foreign)),
            "outsider_pct": outsider_pct,
            "foreign_pct": foreign_pct,
            "label": f"최근 {days}일 방문 {_fmt_count(total)}명",
            "detail": f"외지인 {outsider_pct}% · 외국인 {foreign_pct}%",
        }

    return regions


def fetch_gangwon_visitor_stats(
    *,
    days: int = 7,
    end: date | None = None,
    service_key: str | None = None,
) -> dict[str, Any]:
    end_date = end or (date.today() - timedelta(days=1))
    start_date = end_date - timedelta(days=max(days - 1, 0))
    start_ymd = _fmt_ymd(start_date)
    end_ymd = _fmt_ymd(end_date)

    items = fetch_datalab_items(
        "locgoRegnVisitrDDList",
        start_ymd=start_ymd,
        end_ymd=end_ymd,
        service_key=service_key,
    )
    regions = aggregate_locgo_visitors(items, days=days)

    return {
        "source": "TourAPI DataLab locgoRegnVisitrDDList",
        "updated_at": date.today().isoformat(),
        "period": {"startYmd": start_ymd, "endYmd": end_ymd, "days": days},
        "regions": regions,
    }


def fetch_metco_gangwon_summary(
    *,
    days: int = 7,
    end: date | None = None,
    area_code: str | int = GANGWON_AREA_CD,
    service_key: str | None = None,
) -> dict[str, Any] | None:
    end_date = end or (date.today() - timedelta(days=1))
    start_date = end_date - timedelta(days=max(days - 1, 0))
    start_ymd = _fmt_ymd(start_date)
    end_ymd = _fmt_ymd(end_date)

    items = fetch_datalab_items(
        "metcoRegnVisitrDDList",
        start_ymd=start_ymd,
        end_ymd=end_ymd,
        service_key=service_key,
    )
    code = str(area_code)
    filtered = [i for i in items if str(i.get("areaCode") or "") == code]
    if not filtered:
        return None

    totals = {"local": 0.0, "outsider": 0.0, "foreign": 0.0}
    area_nm = ""
    for item in filtered:
        area_nm = str(item.get("areaNm") or area_nm)
        div = TOU_DIV_LABELS.get(str(item.get("touDivCd") or ""))
        if not div:
            continue
        try:
            totals[div] += float(item.get("touNum") or 0)
        except (TypeError, ValueError):
            pass

    total = sum(totals.values())
    if total <= 0:
        return None

    return {
        "area_code": code,
        "area_nm": area_nm or "강원특별자치도",
        "total": int(round(total)),
        "avg_daily": int(round(total / max(days, 1))),
        "outsider_pct": round(totals["outsider"] / total * 100),
        "foreign_pct": round(totals["foreign"] / total * 100),
        "label": f"강원 전체 최근 {days}일 {_fmt_count(total)}명",
    }


# ---------- LocgoHubTar (중심관광지) ----------


def normalize_hub_item(item: dict[str, Any]) -> dict[str, Any]:
    rank_raw = item.get("hubRank")
    try:
        rank = int(rank_raw)
    except (TypeError, ValueError):
        rank = 999
    lat = _parse_float(item.get("mapY"))
    lng = _parse_float(item.get("mapX"))
    return {
        "code": str(item.get("hubTatsCd") or ""),
        "name": _clean_hub_name(str(item.get("hubTatsNm") or "")),
        "rank": rank,
        "category_l": str(item.get("hubCtgryLclsNm") or ""),
        "category_m": str(item.get("hubCtgryMclsNm") or ""),
        "category": str(item.get("hubCtgryMclsNm") or item.get("hubCtgryLclsNm") or ""),
        "lat": lat,
        "lng": lng,
        "baseYm": str(item.get("baseYm") or ""),
    }


def fetch_hub_spots_for_sigungu(
    *,
    area_cd: int,
    signgu_cd: int,
    base_ym: str | None = None,
    service_key: str | None = None,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    items = _fetch_all_pages(
        HUB_BASE,
        "areaBasedList1",
        {
            "baseYm": base_ym or _default_base_ym(),
            "areaCd": area_cd,
            "signguCd": signgu_cd,
        },
        service_key=service_key,
        num_of_rows=50,
        max_pages=3,
    )
    normalized = [normalize_hub_item(i) for i in items if i.get("hubTatsNm")]
    normalized.sort(key=lambda x: x["rank"])
    return normalized[:top_n]


def fetch_gangwon_hub_spots(
    *,
    base_ym: str | None = None,
    service_key: str | None = None,
    top_n: int = 5,
    throttle_sec: float = 0.12,
) -> dict[str, Any]:
    key = service_key or get_service_key()
    codes = load_gangwon_sigungu_codes()
    base = base_ym or _default_base_ym()
    regions: dict[str, list[dict[str, Any]]] = {}

    for region, meta in codes.get("regions", {}).items():
        if region not in GANGWON_REGIONS:
            continue
        try:
            hubs = fetch_hub_spots_for_sigungu(
                area_cd=int(meta["areaCd"]),
                signgu_cd=int(meta["signguCd"]),
                base_ym=base,
                service_key=key,
                top_n=top_n,
            )
            if hubs:
                regions[region] = hubs
        except TourApiError:
            continue
        if throttle_sec > 0:
            time.sleep(throttle_sec)

    return {
        "source": "TourAPI LocgoHubTarService1 areaBasedList1",
        "updated_at": date.today().isoformat(),
        "baseYm": base,
        "regions": regions,
    }


# ---------- TarRlteTar (연관관광지) ----------


def _anchor_field(item: dict[str, Any], suffix: str) -> str:
    """매뉴얼 baseTatsCd/baseTatsNm (일부 응답은 tatsCd/tatsNm)."""
    for key in (f"baseTats{suffix}", f"tats{suffix}", f"baseTar{suffix}"):
        val = item.get(key)
        if val not in (None, ""):
            return str(val)
    return ""


def normalize_relate_item(item: dict[str, Any]) -> dict[str, Any]:
    rank_raw = item.get("rlteRank")
    try:
        rank = int(rank_raw)
    except (TypeError, ValueError):
        rank = 999
    cat_m = str(item.get("rlteCtgryMclsNm") or "")
    cat_l = str(item.get("rlteCtgryLclsNm") or "")
    cat_s = str(item.get("rlteCtgrySclsNm") or "")
    return {
        "anchor_code": _anchor_field(item, "Cd"),
        "anchor_name": _clean_hub_name(_anchor_field(item, "Nm")),
        "code": str(item.get("rlteTatsCd") or ""),
        "name": _clean_hub_name(str(item.get("rlteTatsNm") or "")),
        "rank": rank,
        "category_l": cat_l,
        "category_m": cat_m,
        "category_s": cat_s,
        "category": cat_m or cat_l or cat_s,
        "region": str(item.get("rlteSignguNm") or item.get("signguNm") or "").strip(),
        "baseYm": str(item.get("baseYm") or ""),
    }


def _group_relate_by_anchor(items: list[dict[str, Any]], *, top_n: int = 5) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in items:
        anchor = row.get("anchor_name") or row.get("anchor_code") or "기타"
        slot = buckets.setdefault(anchor, [])
        if any(x.get("code") == row.get("code") for x in slot):
            continue
        slot.append(
            {
                "code": row["code"],
                "name": row["name"],
                "rank": row["rank"],
                "category": row.get("category") or "",
            }
        )
    for anchor, related in buckets.items():
        related.sort(key=lambda x: x["rank"])
        buckets[anchor] = related[:top_n]
    return buckets


def fetch_relate_spots_for_sigungu(
    *,
    area_cd: int,
    signgu_cd: int,
    base_ym: str | None = None,
    service_key: str | None = None,
    top_n_per_anchor: int = 5,
) -> list[dict[str, Any]]:
    items = _fetch_all_pages(
        RELATE_BASE,
        "areaBasedList1",
        {
            "baseYm": base_ym or _default_base_ym(),
            "areaCd": area_cd,
            "signguCd": signgu_cd,
        },
        service_key=service_key,
        num_of_rows=100,
        max_pages=15,
    )
    normalized = [normalize_relate_item(i) for i in items if i.get("rlteTatsNm")]
    normalized.sort(key=lambda x: (x.get("anchor_name") or "", x["rank"]))
    if top_n_per_anchor <= 0:
        return normalized
    out: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for row in normalized:
        anchor = row.get("anchor_name") or row.get("anchor_code") or ""
        n = counts.get(anchor, 0)
        if n >= top_n_per_anchor:
            continue
        counts[anchor] = n + 1
        out.append(row)
    return out


def search_relate_spots_by_keyword(
    keyword: str,
    *,
    service_key: str | None = None,
    top_n: int = 10,
) -> list[dict[str, Any]]:
    items = _fetch_all_pages(
        RELATE_BASE,
        "searchKeyword1",
        {"keyword": keyword},
        service_key=service_key,
        num_of_rows=50,
        max_pages=2,
    )
    normalized = [normalize_relate_item(i) for i in items if i.get("rlteTatsNm")]
    normalized.sort(key=lambda x: x["rank"])
    return normalized[:top_n]


def fetch_gangwon_relate_spots(
    *,
    base_ym: str | None = None,
    service_key: str | None = None,
    top_n_per_anchor: int = 5,
    throttle_sec: float = 0.12,
) -> dict[str, Any]:
    key = service_key or get_service_key()
    codes = load_gangwon_sigungu_codes()
    base = base_ym or _default_base_ym()
    regions: dict[str, list[dict[str, Any]]] = {}
    by_anchor: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for region, meta in codes.get("regions", {}).items():
        if region not in GANGWON_REGIONS:
            continue
        try:
            pairs = fetch_relate_spots_for_sigungu(
                area_cd=int(meta["areaCd"]),
                signgu_cd=int(meta["signguCd"]),
                base_ym=base,
                service_key=key,
                top_n_per_anchor=top_n_per_anchor,
            )
            if pairs:
                regions[region] = pairs
                by_anchor[region] = _group_relate_by_anchor(pairs, top_n=top_n_per_anchor)
        except TourApiError:
            continue
        if throttle_sec > 0:
            time.sleep(throttle_sec)

    return {
        "source": "TourAPI TarRlteTarService1 areaBasedList1",
        "updated_at": date.today().isoformat(),
        "baseYm": base,
        "regions": regions,
        "by_anchor": by_anchor,
    }


# ---------- PhotoGallery (관광사진) ----------


def normalize_photo_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("galContentId") or ""),
        "title": str(item.get("galTitle") or "").strip(),
        "image": str(item.get("galWebImageUrl") or ""),
        "location": str(item.get("galPhotographyLocation") or ""),
        "month": str(item.get("galPhotographyMonth") or ""),
        "photographer": str(item.get("galPhotographer") or ""),
        "keyword": str(item.get("galSearchKeyword") or ""),
    }


def search_gallery_photos(
    keyword: str,
    *,
    arrange: str = "C",
    num_of_rows: int = 3,
    service_key: str | None = None,
) -> list[dict[str, Any]]:
    items = _fetch_all_pages(
        PHOTO_BASE,
        "gallerySearchList1",
        {"keyword": keyword, "arrange": arrange},
        service_key=service_key,
        num_of_rows=num_of_rows,
        max_pages=1,
    )
    photos = [normalize_photo_item(i) for i in items if i.get("galWebImageUrl")]
    return photos[:num_of_rows]


def _photo_keyword_for_region(region: str) -> str:
    short = region.replace("특별자치도", "").strip()
    return f"강원 {short} 관광"


def fetch_gangwon_region_photos(
    *,
    per_region: int = 2,
    service_key: str | None = None,
    throttle_sec: float = 0.12,
) -> dict[str, Any]:
    key = service_key or get_service_key()
    regions: dict[str, list[dict[str, Any]]] = {}

    for region in GANGWON_REGIONS:
        keyword = _photo_keyword_for_region(region)
        try:
            photos = search_gallery_photos(
                keyword,
                num_of_rows=per_region,
                service_key=key,
            )
            if photos:
                regions[region] = photos
        except TourApiError:
            continue
        if throttle_sec > 0:
            time.sleep(throttle_sec)

    return {
        "source": "TourAPI PhotoGalleryService1 gallerySearchList1",
        "updated_at": date.today().isoformat(),
        "regions": regions,
    }


# ---------- Code enrichment (법정동·생태관광 시군구) ----------


def _item_code_name(item: dict[str, Any]) -> tuple[str, str]:
    code = str(
        item.get("code")
        or item.get("lDongSignguCd")
        or item.get("signguCd")
        or ""
    ).strip()
    name = str(
        item.get("name")
        or item.get("lDongSignguNm")
        or item.get("signguNm")
        or ""
    ).strip()
    return code, name


def _resolve_ldong_regn_cd(*, service_key: str) -> str:
    items = _fetch_all_pages(
        KOR_BASE,
        "ldongCode2",
        {"lDongListYn": "Y"},
        service_key=service_key,
        num_of_rows=100,
        max_pages=5,
    )
    for item in items:
        nm = str(item.get("lDongRegnNm") or "")
        if "강원" in nm:
            return str(item.get("lDongRegnCd") or "51")
    return "51"


def _fetch_ldong_sigungu_list(ldong_regn_cd: str, *, service_key: str) -> list[dict[str, Any]]:
    return _fetch_all_pages(
        KOR_BASE,
        "ldongCode2",
        {"lDongRegnCd": ldong_regn_cd, "lDongListYn": "N"},
        service_key=service_key,
        num_of_rows=100,
        max_pages=3,
    )


def _fetch_eco_sigungu_list(eco_area_code: int, *, service_key: str) -> list[dict[str, Any]]:
    return _fetch_all_pages(
        ECO_BASE,
        "areaCode1",
        {"areaCode": eco_area_code},
        service_key=service_key,
        num_of_rows=100,
        max_pages=3,
    )


def enrich_gangwon_sigungu_codes(*, service_key: str | None = None) -> dict[str, Any]:
    """Kor ldong·Eco 시군구 코드를 gangwon_sigungu_codes.json에 병합."""
    key = service_key or get_service_key()
    codes = load_gangwon_sigungu_codes()
    ldong_regn = _resolve_ldong_regn_cd(service_key=key)
    ldong_items = _fetch_ldong_sigungu_list(ldong_regn, service_key=key)
    eco_items = _fetch_eco_sigungu_list(ECO_GANGWON_AREA_CODE, service_key=key)

    ldong_by_region: dict[str, str] = {}
    for item in ldong_items:
        code, name = _item_code_name(item)
        region = _match_gangwon_region(name)
        if region and code:
            ldong_by_region[region] = code

    eco_by_region: dict[str, int] = {}
    for item in eco_items:
        code, name = _item_code_name(item)
        region = _match_gangwon_region(name)
        if region and code:
            try:
                eco_by_region[region] = int(code)
            except ValueError:
                continue

    for region, meta in codes.get("regions", {}).items():
        if region not in GANGWON_REGIONS:
            continue
        if region in ldong_by_region:
            meta["lDongRegnCd"] = ldong_regn
            meta["lDongSignguCd"] = ldong_by_region[region]
        if region in eco_by_region:
            meta["ecoAreaCode"] = ECO_GANGWON_AREA_CODE
            meta["ecoSigunguCode"] = eco_by_region[region]

    codes["lDongRegnCd"] = ldong_regn
    codes["ecoAreaCode"] = ECO_GANGWON_AREA_CODE
    save_gangwon_sigungu_codes(codes)
    return codes


# ---------- GreenTour (생태관광) ----------


def normalize_eco_item(item: dict[str, Any]) -> dict[str, Any]:
    summary = str(item.get("summary") or "").strip()
    if len(summary) > 180:
        summary = summary[:177] + "…"
    return {
        "id": str(item.get("contentid") or item.get("contentId") or ""),
        "title": str(item.get("title") or "").strip(),
        "summary": summary,
        "addr": str(item.get("addr") or "").strip(),
        "tel": str(item.get("tel") or ""),
        "image": str(item.get("mainimage") or ""),
    }


def fetch_eco_spots_for_sigungu(
    *,
    area_code: int,
    sigungu_code: int,
    service_key: str | None = None,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    items = _fetch_all_pages(
        ECO_BASE,
        "areaBasedList1",
        {"areaCode": area_code, "sigunguCode": sigungu_code},
        service_key=service_key,
        num_of_rows=50,
        max_pages=2,
    )
    normalized = [normalize_eco_item(i) for i in items if i.get("title")]
    return normalized[:top_n]


def fetch_gangwon_eco_spots(
    *,
    service_key: str | None = None,
    top_n: int = 5,
    throttle_sec: float = 0.12,
) -> dict[str, Any]:
    key = service_key or get_service_key()
    codes = load_gangwon_sigungu_codes()
    regions: dict[str, list[dict[str, Any]]] = {}

    for region, meta in codes.get("regions", {}).items():
        if region not in GANGWON_REGIONS:
            continue
        area_code = meta.get("ecoAreaCode")
        sigungu_code = meta.get("ecoSigunguCode")
        if area_code is None or sigungu_code is None:
            continue
        try:
            spots = fetch_eco_spots_for_sigungu(
                area_code=int(area_code),
                sigungu_code=int(sigungu_code),
                service_key=key,
                top_n=top_n,
            )
            if spots:
                regions[region] = spots
        except TourApiError:
            continue
        if throttle_sec > 0:
            time.sleep(throttle_sec)

    return {
        "source": "TourAPI GreenTourService1 areaBasedList1",
        "updated_at": date.today().isoformat(),
        "ecoAreaCode": codes.get("ecoAreaCode", ECO_GANGWON_AREA_CODE),
        "regions": regions,
    }


# ---------- KorService2 (국문 관광정보) ----------


def _fmt_festival_period(start: str, end: str) -> str:
    def fmt(ymd: str) -> str:
        ymd = (ymd or "").strip()
        if len(ymd) >= 8:
            return f"{ymd[4:6]}.{ymd[6:8]}"
        return ymd

    s, e = fmt(start), fmt(end)
    if s and e:
        return f"{s} ~ {e}"
    return s or e or ""


def normalize_kor_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("contentid") or ""),
        "title": str(item.get("title") or "").strip(),
        "addr": str(item.get("addr1") or item.get("addr2") or "").strip(),
        "image": str(item.get("firstimage") or item.get("firstimage2") or ""),
        "tel": str(item.get("tel") or ""),
        "typeId": str(item.get("contenttypeid") or ""),
        "mapX": item.get("mapx"),
        "mapY": item.get("mapy"),
    }


def normalize_kor_festival(item: dict[str, Any], *, place: str) -> dict[str, Any]:
    start = str(item.get("eventstartdate") or "")
    end = str(item.get("eventenddate") or "")
    base = normalize_kor_item(item)
    desc = str(item.get("eventplace") or base["addr"] or "").strip()
    return {
        **base,
        "place": place,
        "period": _fmt_festival_period(start, end),
        "desc": desc[:120] if desc else "",
        "eventStartDate": start,
        "eventEndDate": end,
    }


def fetch_kor_spots_for_sigungu(
    *,
    ldong_regn_cd: str,
    ldong_signgu_cd: str,
    service_key: str | None = None,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    items = _fetch_all_pages(
        KOR_BASE,
        "areaBasedList2",
        {
            "lDongRegnCd": ldong_regn_cd,
            "lDongSignguCd": ldong_signgu_cd,
            "contentTypeId": KOR_CONTENT_TYPE_ATTRACTION,
            "arrange": "O",
        },
        service_key=service_key,
        num_of_rows=50,
        max_pages=2,
    )
    normalized = [normalize_kor_item(i) for i in items if i.get("title")]
    return normalized[:top_n]


def fetch_kor_festivals_for_sigungu(
    *,
    ldong_regn_cd: str,
    ldong_signgu_cd: str,
    region: str,
    year: int | None = None,
    service_key: str | None = None,
    top_n: int = 20,
) -> list[dict[str, Any]]:
    yr = year or date.today().year
    items = _fetch_all_pages(
        KOR_BASE,
        "searchFestival2",
        {
            "lDongRegnCd": ldong_regn_cd,
            "lDongSignguCd": ldong_signgu_cd,
            "eventStartDate": f"{yr}0101",
            "eventEndDate": f"{yr}1231",
            "arrange": "O",
        },
        service_key=service_key,
        num_of_rows=50,
        max_pages=3,
    )
    normalized = [
        normalize_kor_festival(i, place=region)
        for i in items
        if i.get("title")
    ]
    return normalized[:top_n]


def fetch_gangwon_kor_spots(
    *,
    service_key: str | None = None,
    top_n: int = 5,
    throttle_sec: float = 0.12,
) -> dict[str, Any]:
    key = service_key or get_service_key()
    codes = load_gangwon_sigungu_codes()
    regions: dict[str, list[dict[str, Any]]] = {}

    for region, meta in codes.get("regions", {}).items():
        if region not in GANGWON_REGIONS:
            continue
        regn = meta.get("lDongRegnCd")
        signgu = meta.get("lDongSignguCd")
        if not regn or not signgu:
            continue
        try:
            spots = fetch_kor_spots_for_sigungu(
                ldong_regn_cd=str(regn),
                ldong_signgu_cd=str(signgu),
                service_key=key,
                top_n=top_n,
            )
            if spots:
                regions[region] = spots
        except TourApiError:
            continue
        if throttle_sec > 0:
            time.sleep(throttle_sec)

    return {
        "source": "TourAPI KorService2 areaBasedList2",
        "updated_at": date.today().isoformat(),
        "lDongRegnCd": codes.get("lDongRegnCd"),
        "regions": regions,
    }


def fetch_gangwon_kor_festivals(
    *,
    service_key: str | None = None,
    year: int | None = None,
    throttle_sec: float = 0.12,
) -> dict[str, Any]:
    key = service_key or get_service_key()
    codes = load_gangwon_sigungu_codes()
    yr = year or date.today().year
    by_region: dict[str, list[dict[str, Any]]] = {}
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for region, meta in codes.get("regions", {}).items():
        if region not in GANGWON_REGIONS:
            continue
        regn = meta.get("lDongRegnCd")
        signgu = meta.get("lDongSignguCd")
        if not regn or not signgu:
            continue
        try:
            festivals = fetch_kor_festivals_for_sigungu(
                ldong_regn_cd=str(regn),
                ldong_signgu_cd=str(signgu),
                region=region,
                year=yr,
                service_key=key,
            )
            if festivals:
                by_region[region] = festivals
                for fest in festivals:
                    fid = fest.get("id") or fest.get("title")
                    if fid in seen:
                        continue
                    seen.add(fid)
                    items.append(fest)
        except TourApiError:
            continue
        if throttle_sec > 0:
            time.sleep(throttle_sec)

    items.sort(key=lambda x: (x.get("eventStartDate") or "", x.get("title") or ""))

    return {
        "source": "TourAPI KorService2 searchFestival2",
        "updated_at": date.today().isoformat(),
        "year": yr,
        "lDongRegnCd": codes.get("lDongRegnCd"),
        "regions": by_region,
        "items": items,
    }
