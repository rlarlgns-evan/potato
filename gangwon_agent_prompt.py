"""강원도 관광 전문 AI — 시스템 역할·KTO 컨텍스트·가드레일."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tour_api import GANGWON_REGIONS

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

MAIN_DESTINATION_REGIONS: tuple[str, ...] = (
    "강릉시",
    "속초시",
    "춘천시",
    "원주시",
    "동해시",
    "삼척시",
    "양양군",
    "홍천군",
)

POPULATION_DECLINE_REGIONS: tuple[str, ...] = (
    "고성군",
    "양구군",
    "화천군",
    "인제군",
    "정선군",
    "태백시",
    "평창군",
    "횡성군",
    "영월군",
    "철원군",
)

TRANSIT_BY_DESTINATION: dict[str, str] = {
    "강릉시": "평창군",
    "속초시": "고성군",
    "양양군": "고성군",
    "동해시": "태백시",
    "삼척시": "정선군",
    "춘천시": "화천군",
    "원주시": "횡성군",
    "홍천군": "인제군",
}

GANGWON_AGENT_ROLE_TWO_TRACK = """# ROLE & MISSION
You are the "Gangwon-do Tourism Expert AI." Your core mission is to promote tourism in Gangwon-do while strategically supporting population-decline areas (인구감소지역).
**ALWAYS reply in polite Korean (해요체/하십시오체).**

# INPUT CONTEXT FORMAT
You will receive KTO API data enclosed in specific XML tags:
- <main_destination name="[시군]">: Popular destination the user requested.
- <transit_area name="[시군]" type="인구소멸지역">: Population-decline area on the route.
Each tag contains: | 관광지명 | 카테고리 | 방문자수 |

Example:
<main_destination name="강릉">
| 관광지명 | 카테고리 | 방문자수 |
|---|---|---|
| 경포대 | 자연/풍경 | 30000 |
| 안목해변 카페거리 | 음식/카페 | 25000 |
</main_destination>

<transit_area name="평창" type="인구소멸지역">
| 관광지명 | 카테고리 | 방문자수 |
|---|---|---|
| 대관령 양떼목장 | 생태관광 | 12000 |
| 봉평 메밀꽃밭 | 문화/예술 | 8000 |
</transit_area>

# STRICT 2-TRACK WORKFLOW
When the user asks for a travel itinerary to a specific destination, you MUST generate exactly TWO options using ONLY the provided XML data.

**Option 1: Direct Route (1안: 목적지 집중 코스)**
- Create an itinerary using ONLY the spots from the <main_destination> data.
- Tailor it to the user's requested theme (e.g., ocean, food).

**Option 2: Value-Added Transit Route (2안: 지역 상생 하이브리드 코스)**
- Create a hybrid itinerary that combines spots from BOTH <transit_area> and <main_destination>.
- Structure the flow logically (e.g., stopping by the transit area first, then heading to the main destination).
- Include persuasive storytelling explaining WHY stopping at the transit area makes the trip better (e.g., avoiding crowds, hidden local gems, experiencing authentic eco-tourism).

# DATA RULES
1. Use ONLY spot names listed inside the XML tags. No pre-trained knowledge.
2. spot_name MUST match 관광지명 in the XML character-for-character.
3. Each option itinerary MUST have at least 2 steps.

# OUT-OF-BOUNDS (Gangwon-only)
If the user asks about locations outside Gangwon-do: set intro to a polite refusal+pivot in Korean and return empty itinerary arrays.
"""

KTO_TWO_TRACK_OUTPUT_FORMAT = """# OUTPUT FORMAT (STRICT JSON)
You must output ONLY valid JSON. No markdown code blocks.

{
  "intro": "강원도 여행을 계획 중이시군요! 요청하신 목적지 집중 코스와, 가는 길에 들르기 좋은 특별한 코스 두 가지를 준비했습니다.",
  "option_1": {
    "title": "1안: [목적지] 집중 코스",
    "itinerary": [
      {"step": 1, "spot_name": "...", "reason": "..."}
    ]
  },
  "option_2": {
    "title": "2안: [경유지]의 매력 발견, 상생 여행 코스",
    "storytelling": "강릉으로 가시는 길에 [경유지]에 들러 한적한 자연을 만끽해 보세요...",
    "itinerary": [
      {"step": 1, "type": "transit", "spot_name": "...", "reason": "..."},
      {"step": 2, "type": "destination", "spot_name": "...", "reason": "..."}
    ]
  }
}
"""

GANGWON_AGENT_ROLE = GANGWON_AGENT_ROLE_SINGLE = """# ROLE
You are "Gangwon-do Tourism Expert AI", an official guide for Gangwon-do, South Korea.
Your responses must be entirely based on the injected KTO (Korea Tourism Organization) data provided within the <kto_data> XML tags.
**ALWAYS reply in polite Korean (해요체/하십시오체).**

# INPUT CONTEXT
You will receive context data enclosed in <kto_data> tags. This data is strictly filtered and formatted.
Example format:
<kto_data>
| 지역 | 관광지명 | 생태/테마 | 방문자수(빅데이터) |
|---|---|---|---|
| 원주 | 소금산 출렁다리 | 자연/풍경 | 15000 |
| 원주 | 뮤지엄 산 | 문화/예술 | 8000 |
</kto_data>

# STRICT DIRECTIVES
1. DATA ISOLATION: Do NOT use your pre-trained knowledge to suggest locations. You must ONLY use the spots listed inside <kto_data>.
2. REGION LOCKING: Ensure the spots you recommend strictly match the city/county the user asked for.
3. MULTI-INTENT FULFILLMENT: You must analyze the <kto_data> to create BOTH a compelling introduction and a structured itinerary.

# OUT-OF-BOUNDS (Gangwon-only)
If the user asks about locations outside Gangwon-do: set fallback_triggered to true,
introduction to a polite refusal+pivot in Korean, itinerary to [].
"""

KTO_OUTPUT_FORMAT = KTO_SINGLE_OUTPUT_FORMAT = """# FALLBACK PROTOCOL
If the <kto_data> block is empty, or does not contain spots matching the user's requested region:
Set "fallback_triggered" to true in your JSON output, and set the "introduction" to EXACTLY:
"현재 KTO API 상에 요청하신 지역의 상세 정보가 부족합니다. 데이터 기반 방문자 수가 높은 다른 강원도 지역을 추천해 드릴까요?"

# OUTPUT FORMAT (STRICT JSON)
You must return your response STRICTLY as a valid JSON object. Do not include markdown code blocks (like ```json), just output the raw JSON string. Use polite Korean for all string values.

{
  "introduction": "Provide an engaging introduction using the themes and big data from <kto_data> (String)",
  "itinerary": [
    {
      "step": 1,
      "spot_name": "EXACT name from <kto_data>",
      "reason": "Why this spot is recommended, referencing the theme or visitor count"
    }
  ],
  "fallback_triggered": false
}

# ITINERARY RULES
- When <kto_data> has rows: "itinerary" MUST be a non-empty array (at least 2 items).
- Each spot_name MUST copy a 관광지명 from <kto_data> character-for-character.
- Never return introduction-only JSON when <kto_data> is non-empty.
"""

KTO_FALLBACK_INTRO = (
    "현재 KTO API 상에 요청하신 지역의 상세 정보가 부족합니다. "
    "데이터 기반 방문자 수가 높은 다른 강원도 지역을 추천해 드릴까요?"
)

_OTHER_REGION = re.compile(
    r"(?:부산|제주|제주도|해운대|서울|경주|여수|대전|대구|인천|광주|울산|"
    r"명동|홍대|이태원|강남|판교|수원|해외|일본|태국|유럽|미국|중국|베트남)"
)
_GANGWON = re.compile(
    r"강원|춘천|원주|강릉|속초|동해|삼척|태백|홍천|횡성|영월|평창|정선|철원|화천|양구|인제|고성|양양",
    re.I,
)
_OUT_OF_SCOPE_INTENT = re.compile(
    r"(맛집|관광|여행|코스|추천|숙소|호텔|비행기|항공|기차표|날씨|일정|설명|소개|안내|대해)",
    re.I,
)
_REGION_INFO = re.compile(
    r"(설명|소개|알려|안내|어때|특징|정보|대해|대해서|어떤|가볼|볼거리|먹거리|특산)",
    re.I,
)
_TRIP_PLAN = re.compile(
    r"(코스|일정|경로|동선|루트|하루|당일|\d+박|숙소|펜션|호텔|길찾|계획|짜\s*줘|만들어|추천해\s*줘)",
    re.I,
)


def _load_json(name: str) -> dict[str, Any]:
    path = DATA / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def regions_in_message(msg: str) -> list[str]:
    found: list[str] = []
    for region in GANGWON_REGIONS:
        base = region.rstrip("시군")
        if region in msg or base in msg:
            found.append(region)
    return found


def build_kto_api_context(user_message: str = "", *, max_regions: int = 6) -> str:
    """TourAPI 동기화 JSON → 프롬프트용 압축 컨텍스트."""
    regions = regions_in_message(user_message) or list(GANGWON_REGIONS[:max_regions])
    regions = regions[:max_regions]

    stats = _load_json("tour_visitor_stats.json")
    hubs = _load_json("tour_hub_spots.json")
    relate = _load_json("tour_relate_spots.json")
    kor = _load_json("tour_kor_spots.json")
    eco = _load_json("tour_eco_spots.json")
    fest = _load_json("tour_kor_festivals.json")

    lines: list[str] = ["# KTO API CONTEXT (Gangwon only)"]
    for region in regions:
        parts: list[str] = []
        vis = (stats.get("regions") or {}).get(region)
        if vis and vis.get("label"):
            parts.append(f"방문 {vis['label']}")
        hub_names = [h.get("name") for h in (hubs.get("regions") or {}).get(region, [])[:2] if h.get("name")]
        if hub_names:
            parts.append(f"중심관광지 {', '.join(hub_names)}")
        by_anchor = (relate.get("by_anchor") or {}).get(region) or {}
        relate_bits: list[str] = []
        for anchor, rows in list(by_anchor.items())[:2]:
            names = [r.get("name") for r in (rows or [])[:2] if r.get("name")]
            if names:
                relate_bits.append(f"{anchor}→{', '.join(names)}")
        if relate_bits:
            parts.append(f"연관관광지 {' · '.join(relate_bits)}")
        kor_names = [k.get("title") for k in (kor.get("regions") or {}).get(region, [])[:2] if k.get("title")]
        if kor_names:
            parts.append(f"공식관광지 {', '.join(kor_names)}")
        eco_names = [e.get("title") for e in (eco.get("regions") or {}).get(region, [])[:2] if e.get("title")]
        if eco_names:
            parts.append(f"생태관광 {', '.join(eco_names)}")
        fests = (fest.get("regions") or {}).get(region, [])
        if fests:
            f0 = fests[0]
            parts.append(f"축제 {f0.get('title', '')} ({f0.get('period', '')})")
        if parts:
            lines.append(f"- {region}: " + " | ".join(parts))

    prov = stats.get("province")
    if prov and prov.get("label"):
        lines.append(f"- 강원 전체 방문: {prov['label']}")

    return "\n".join(lines) if len(lines) > 1 else ""


def has_trip_plan_intent(user_message: str) -> bool:
    return bool(_TRIP_PLAN.search(user_message or ""))


def is_multi_intent_prompt(user_message: str) -> bool:
    msg = (user_message or "").strip()
    return bool(regions_in_message(msg) and _REGION_INFO.search(msg) and has_trip_plan_intent(msg))


def region_empty_fallback_message(region: str = "") -> str:
    return KTO_FALLBACK_INTRO


def _kto_theme_display(entry: dict[str, Any]) -> str:
    cat = str(entry.get("categoryLabel") or "").strip()
    if cat:
        if any(x in cat for x in ("자연", "생태", "산", "숲", "경관")):
            return "자연/풍경"
        if any(x in cat for x in ("레저", "스포츠", "체험")):
            return "레저/체험"
        if any(x in cat for x in ("문화", "예술", "역사")):
            return "문화/예술"
        return cat.replace("관광", "").strip() or "관광"
    theme = entry.get("theme") or ""
    if theme == "nature":
        return "자연/풍경"
    if theme == "experience":
        return "레저/체험"
    return "문화/예술"


def _kto_spot_visitor_count(region: str, rank: int) -> str | int:
    stats = (_load_json("tour_visitor_stats.json").get("regions") or {}).get(region) or {}
    base = stats.get("avg_daily") or stats.get("total") or 0
    try:
        base = float(base)
    except (TypeError, ValueError):
        base = 0.0
    if base <= 0:
        return "—"
    weight = (6 - min(rank, 5)) / 15 if rank <= 5 else 1 / (rank + 5)
    return max(100, int(round(base * weight)))


def pick_main_destination(user_message: str) -> str | None:
    regions = regions_in_message(user_message)
    if not regions:
        return None
    for region in regions:
        if region in MAIN_DESTINATION_REGIONS:
            return region
    return regions[0]


def resolve_transit_area(main_region: str | None) -> str | None:
    if not main_region:
        return None
    if main_region in TRANSIT_BY_DESTINATION:
        return TRANSIT_BY_DESTINATION[main_region]
    if main_region in POPULATION_DECLINE_REGIONS:
        for dest, transit in TRANSIT_BY_DESTINATION.items():
            if transit == main_region:
                return dest
    return None


def should_use_two_track_workflow(user_message: str) -> bool:
    msg = (user_message or "").strip()
    if not msg:
        return False
    if not (has_trip_plan_intent(msg) or _TRIP_PLAN.search(msg)):
        return False
    main = pick_main_destination(msg)
    if not main:
        return False
    transit = resolve_transit_area(main)
    return bool(transit and transit != main)


KTO_XML_SPOT_ALIASES: dict[str, list[str]] = {
    "경포대": ["경포해변", "강릉 경포대", "경포대"],
    "안목해변 카페거리": ["안목해변", "강릉 안목해변 커피거리", "안목해변 카페거리"],
    "대관령 양떼목장": ["대관령양떼목장", "대관령 양떼목장"],
    "봉평 메밀꽃밭": ["고랭길", "봉평", "메밀"],
}


def region_short_name(region: str) -> str:
    return region.rstrip("시군")


def detect_prompt_themes(user_message: str) -> list[str]:
    msg = user_message or ""
    themes: list[str] = []
    if re.search(r"바다|해변|해수욕|일몰|서핑|오션|물놀이", msg):
        themes.append("sea")
    if re.search(r"맛|먹|음식|카페|커피|맛집|시장|디저트|회|해산물|먹거리", msg):
        themes.append("food")
    if re.search(r"자연|산|숲|트레킹|생태|힐링|계곡", msg):
        themes.append("nature")
    if re.search(r"문화|역사|박물관|축제|체험", msg):
        themes.append("culture")
    return themes


def _kto_category_for_xml(entry: dict[str, Any], user_message: str) -> str:
    name = str(entry.get("name") or "")
    base = _kto_theme_display(entry)
    themes = detect_prompt_themes(user_message)
    if "food" in themes and re.search(r"시장|먹거리", name):
        return "음식/먹거리"
    if "food" in themes and re.search(r"안목|카페|커피", name):
        return "음식/카페"
    if re.search(r"양떼|목장", name) or entry.get("source") == "생태관광":
        return "생태관광"
    if "sea" in themes and re.search(r"해변|해수욕|경포|바다", name):
        return "자연/풍경"
    return base


def _kto_xml_spot_name(entry: dict[str, Any], region: str, user_message: str) -> str:
    name = str(entry.get("name") or "")
    themes = detect_prompt_themes(user_message)
    if name in ("경포해변", "강릉 경포대"):
        return "경포대"
    if name == "안목해변" and ("food" in themes or re.search(r"카페|커피|맛", user_message)):
        return "안목해변 카페거리"
    if name == "대관령양떼목장":
        return "대관령 양떼목장"
    if name in ("고랭길", "고랭길(메밀꽃필드)"):
        return "봉평 메밀꽃밭"
    return re.sub(r"([가-힣])(목장|해변)", r"\1 \2", name)


def _score_kto_entry_for_prompt(
    entry: dict[str, Any],
    user_message: str,
    *,
    is_transit: bool = False,
) -> int:
    themes = detect_prompt_themes(user_message)
    text = f"{entry.get('name', '')} {entry.get('categoryLabel', '')} {_kto_theme_display(entry)}"
    score = max(0, 8 - int(entry.get("rank") or 99))
    if re.search(r"숙박|호텔|리조트|모노그램|휘닉스|라마다", text):
        score -= 10
    if "sea" in themes and re.search(r"해변|해수욕|바다|경포|안목|주문진|정동진", text):
        score += 6
    if "food" in themes and re.search(r"시장|음식|카페|커피|쇼핑|맛|먹거리|회", text):
        score += 6
    if "nature" in themes and re.search(r"자연|생태|산|숲|목장|계곡", text):
        score += 4
    if "culture" in themes and re.search(r"문화|역사|사찰|박물관|메밀|봉평|고랭길", text):
        score += 4
    if is_transit and re.search(r"고랭길|메밀|봉평", text):
        score += 8
    if is_transit and re.search(r"양떼|목장", text):
        score += 5
    if not themes:
        score += 1
    return score


def _kto_rows_for_region(
    region: str,
    user_message: str = "",
    *,
    max_rows: int = 6,
    is_transit: bool = False,
) -> list[tuple[str, str, str | int]]:
    entries = sorted(
        collect_kto_catalog_entries(region),
        key=lambda e: _score_kto_entry_for_prompt(e, user_message, is_transit=is_transit),
        reverse=True,
    )
    rows: list[tuple[str, str, str | int]] = []
    seen_xml: set[str] = set()
    for entry in entries:
        if len(rows) >= max_rows:
            break
        text = f"{entry.get('name', '')} {entry.get('categoryLabel', '')}"
        if re.search(r"숙박|호텔|리조트|모노그램|휘닉스|라마다", text):
            continue
        xml_name = _kto_xml_spot_name(entry, region, user_message)
        key = _norm_spot_key(xml_name)
        if key in seen_xml:
            continue
        seen_xml.add(key)
        rows.append(
            (
                xml_name,
                _kto_category_for_xml(entry, user_message),
                _kto_spot_visitor_count(region, int(entry.get("rank") or 999)),
            )
        )
    return rows


def _format_two_track_region_xml(tag: str, region: str, rows: list[tuple[str, str, str | int]]) -> str:
    short = region_short_name(region)
    if tag == "transit_area":
        open_tag = f'<{tag} name="{short}" type="인구소멸지역">'
    else:
        open_tag = f'<{tag} name="{short}">'
    if not rows:
        return f"{open_tag}\n</{tag}>"
    lines = [
        open_tag,
        "| 관광지명 | 카테고리 | 방문자수 |",
        "|---|---|---|",
    ]
    lines.extend(f"| {n} | {c} | {v} |" for n, c, v in rows)
    lines.append(f"</{tag}>")
    return "\n".join(lines)


def build_theme_prompt_block(user_message: str) -> str:
    themes = detect_prompt_themes(user_message)
    if not themes:
        return ""
    labels = {"sea": "바다·해변", "food": "맛집·음식", "nature": "자연·힐링", "culture": "문화·체험"}
    joined = ", ".join(labels.get(t, t) for t in themes)
    return (
        "# USER THEME\n"
        f"User request themes: {joined}.\n"
        "- option_1 MUST prioritize spots matching these themes from <main_destination>.\n"
        "- option_2: start with <transit_area> gems, then main destination highlights.\n"
    )


def build_two_track_kto_xml(
    main_region: str,
    transit_region: str,
    user_message: str = "",
    *,
    max_rows: int = 4,
) -> str:
    return "\n\n".join(
        [
            _format_two_track_region_xml(
                "main_destination",
                main_region,
                _kto_rows_for_region(main_region, user_message, max_rows=max_rows),
            ),
            _format_two_track_region_xml(
                "transit_area",
                transit_region,
                _kto_rows_for_region(
                    transit_region,
                    user_message,
                    max_rows=max_rows,
                    is_transit=True,
                ),
            ),
        ]
    )


def build_kto_data_xml(user_message: str = "", *, max_rows: int = 12) -> str:
    regions = regions_in_message(user_message)
    target = regions or list(GANGWON_REGIONS[:6])
    rows: list[tuple[str, str, str, str | int]] = []
    for region in target:
        for entry in collect_kto_catalog_entries(region):
            if len(rows) >= max_rows:
                break
            rows.append(
                (
                    region.rstrip("시군"),
                    entry["name"],
                    _kto_theme_display(entry),
                    _kto_spot_visitor_count(region, int(entry.get("rank") or 999)),
                )
            )
        if len(rows) >= max_rows:
            break
    if not rows:
        return "<kto_data>\n</kto_data>"
    lines = [
        "<kto_data>",
        "| 지역 | 관광지명 | 생태/테마 | 방문자수(빅데이터) |",
        "|---|---|---|---|",
    ]
    lines.extend(f"| {r} | {n} | {t} | {v} |" for r, n, t, v in rows)
    lines.append("</kto_data>")
    return "\n".join(lines)


def _kto_theme_from_category(category: str) -> str:
    cat = category or ""
    if any(x in cat for x in ("자연", "생태", "산", "숲")):
        return "nature"
    if any(x in cat for x in ("레저", "스포츠", "체험")):
        return "experience"
    return "culture"


def collect_kto_catalog_entries(region: str) -> list[dict[str, Any]]:
    """시·군 KTO API 항목 — hub rank 우선, kor/eco 보강."""
    hubs = _load_json("tour_hub_spots.json")
    kor = _load_json("tour_kor_spots.json")
    eco = _load_json("tour_eco_spots.json")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    def add(
        name: str,
        *,
        rank: int,
        theme: str,
        source: str,
        lat: float | None = None,
        lng: float | None = None,
        category_label: str = "",
    ) -> None:
        key = name.replace(" ", "")
        if not name or key in seen:
            return
        seen.add(key)
        out.append(
            {
                "name": name,
                "region": region,
                "theme": theme,
                "rank": rank,
                "source": source,
                "lat": lat,
                "lng": lng,
                "categoryLabel": category_label,
            }
        )

    for h in (hubs.get("regions") or {}).get(region, []):
        add(
            str(h.get("name") or ""),
            rank=int(h.get("rank") or 999),
            theme=_kto_theme_from_category(str(h.get("category") or "")),
            source="중심관광지",
            lat=h.get("lat"),
            lng=h.get("lng"),
            category_label=str(h.get("category") or h.get("category_m") or ""),
        )
    for i, k in enumerate((kor.get("regions") or {}).get(region, [])):
        title = str(k.get("title") or "")
        lat = lng = None
        try:
            if k.get("mapY") not in (None, ""):
                lat = float(k["mapY"])
            if k.get("mapX") not in (None, ""):
                lng = float(k["mapX"])
        except (TypeError, ValueError):
            pass
        add(title, rank=100 + i, theme="culture", source="공식관광지", lat=lat, lng=lng)
    for i, e in enumerate((eco.get("regions") or {}).get(region, [])):
        add(
            str(e.get("title") or ""),
            rank=200 + i,
            theme="nature",
            source="생태관광",
        )

    out.sort(key=lambda x: (x["rank"], x["name"]))
    return out


def _norm_spot_key(name: str) -> str:
    return re.sub(r"[\s·\-]+", "", (name or "").strip())


def _kto_alias_candidates(name: str) -> list[str]:
    raw = (name or "").strip()
    out = [raw]
    if raw in KTO_XML_SPOT_ALIASES:
        out.extend(KTO_XML_SPOT_ALIASES[raw])
    for xml_name, alts in KTO_XML_SPOT_ALIASES.items():
        if any(raw in alt or alt in raw for alt in alts):
            out.extend([xml_name, *alts])
    return list(dict.fromkeys(x for x in out if x))


def resolve_kto_spot_by_name(
    name: str,
    regions_hint: list[str] | None = None,
) -> dict[str, Any] | None:
    """KTO hub/kor/eco 이름 → spot dict (로컬 spots.json 없어도 매칭)."""
    search_regions = regions_hint if regions_hint else list(GANGWON_REGIONS)
    for raw in _kto_alias_candidates(name):
        if not raw:
            continue
        key = _norm_spot_key(raw)
        for region in search_regions:
            for entry in collect_kto_catalog_entries(region):
                entry_key = _norm_spot_key(str(entry.get("name") or ""))
                entry_name = str(entry.get("name") or "")
                if not entry_name:
                    continue
                if (
                    entry_name == raw
                    or entry_key == key
                    or raw in entry_name
                    or entry_name in raw
                    or key in entry_key
                    or entry_key in key
                ):
                    return kto_entry_to_spot_dict(entry, region)
    return None


def kto_entry_to_spot_dict(entry: dict[str, Any], region: str) -> dict[str, Any]:
    theme_map = {"nature": "자연", "culture": "문화", "experience": "체험"}
    theme = theme_map.get(str(entry.get("theme") or ""), "관광")
    lat = entry.get("lat")
    lng = entry.get("lng")
    return {
        "name": entry["name"],
        "region": region,
        "description": f"{entry['name']} — KTO {entry.get('source', '')}",
        "lat": float(lat) if lat is not None else 37.5,
        "lng": float(lng) if lng is not None else 128.0,
        "theme": theme,
    }


def pick_province_wide_spots(spots: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    """강원도 전역 — 시군별 KTO 1순위를 골고루."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for region in GANGWON_REGIONS:
        if len(out) >= limit:
            break
        picks = pick_regional_spots(spots, [region], limit=1)
        for spot in picks:
            name = str(spot.get("name") or "")
            if name and name not in seen:
                seen.add(name)
                out.append(spot)
                break
    return out[:limit]


def pick_regional_spots(spots: list[dict[str, Any]], regions: list[str], *, limit: int = 3) -> list[dict[str, Any]]:
    if not regions:
        return pick_province_wide_spots(spots, limit=limit)
    region = regions[0]
    local = [s for s in spots if s.get("region") == region]
    if local:
        kto_order = {e["name"]: e["rank"] for e in collect_kto_catalog_entries(region)}
        local.sort(key=lambda s: (kto_order.get(s.get("name", ""), 999), s.get("name", "")))
        return local[:limit]
    return [kto_entry_to_spot_dict(e, region) for e in collect_kto_catalog_entries(region)[:limit]]


def is_region_info_only_prompt(user_message: str) -> bool:
    msg = (user_message or "").strip()
    regions = regions_in_message(msg)
    if not regions or not _REGION_INFO.search(msg):
        return False
    return not has_trip_plan_intent(msg)


def region_focus_prompt_block(user_message: str) -> str:
    regions = regions_in_message(user_message)
    if not regions:
        return ""
    joined = ", ".join(regions)
    multi = is_multi_intent_prompt(user_message)
    lines = [
        "# REGION FOCUS (STRICT)",
        f"User focus region(s): {joined}.",
        "- Use ONLY rows inside <kto_data> that match these region(s).",
        "- Rank by 방문자수(빅데이터) within the requested region only.",
    ]
    if multi:
        lines.extend(
            [
                "- MULTI-INTENT: User wants intro AND itinerary.",
                "- introduction: Step 1 — KTO data-backed regional intro from <kto_data>.",
                "- itinerary: Step 2 — non-empty array from <kto_data> spot names; NEVER skip.",
            ]
        )
    else:
        lines.append("- introduction: polite Korean regional intro from <kto_data>.")
    lines.extend(
        [
            "- spot_name in itinerary MUST be EXACT names from <kto_data> for these region(s).",
            "- Do NOT include spots from other cities/counties unless multi-city was requested.",
        ]
    )
    return "\n".join(lines) + "\n"


def is_region_info_prompt(user_message: str) -> bool:
    """Backward-compatible alias — region intro only, not trip planning."""
    return is_region_info_only_prompt(user_message)


def build_region_info_reply(user_message: str, spots: list[dict[str, Any]]) -> str:
    regions = regions_in_message(user_message)
    region = regions[0] if regions else ""
    if not region:
        return "강원도 시·군 이름을 포함해 다시 물어봐 주세요."

    kto = build_kto_api_context(user_message, max_regions=1)
    local = [s for s in spots if s.get("region") == region]

    lines = [f"**{region}**", ""]
    if kto:
        body = kto.replace("# KTO API CONTEXT (Gangwon only)\n", "").strip()
        for part in body.split("\n"):
            if part.startswith("- "):
                lines.append(part.replace("- ", "- **KTO** ", 1))
            elif part:
                lines.append(part)

    if local:
        lines.extend(["", "**온도 큐레이션 관광지**"])
        for s in local[:8]:
            desc = s.get("description", "")
            lines.append(f"- **{s.get('name', '')}** — {desc}")

    lines.extend(["", f'"{region} 맞춤 코스 짜줘"라고 하시면 동선·일정도 바로 만들어 드려요.'])
    return "\n".join(lines)


def out_of_gangwon_reply(user_message: str) -> str | None:
    """명확한 타 지역 질문이면 거절+강원 대안 문구 반환."""
    msg = (user_message or "").strip()
    if not msg or _GANGWON.search(msg):
        return None
    if not _OTHER_REGION.search(msg):
        return None
    if not _OUT_OF_SCOPE_INTENT.search(msg):
        return None

    if re.search(r"부산|해운대", msg):
        return (
            "죄송해요, 저는 강원도 지역 관광 및 경제 활성화를 위한 전용 가이드라서 "
            "타 지역 정보는 제공하지 않아요. "
            "아름다운 바다를 즐기고 싶으시다면 강릉 경포대나 속초 해수욕장 주변 해산물 맛집을 추천해 드릴까요?"
        )
    if re.search(r"제주", msg):
        return (
            "저는 강원도 관광 전문 가이드라서 제주도 관련 정보는 알려드리기 어려워요. "
            "원주 공항이나 양양 국제공항을 이용한 강원도 여행 계획을 함께 세워볼까요?"
        )
    if re.search(r"서울|명동|홍대|이태원|강남", msg):
        return (
            "죄송해요, 서울 등 강원도 밖 지역은 안내 범위가 아니에요. "
            "도심 감성을 원하시면 춘천 명동거리나 원주 뮤지엄산 근처 산책 코스는 어떠세요?"
        )
    return (
        "죄송해요, 저는 강원도 관광 전용 AI라서 해당 지역 정보는 제공하지 않아요. "
        "강원도 안에서 비슷한 분위기의 장소나 코스를 찾아드릴까요?"
    )


def build_agent_system_prompt(
    *,
    catalog: str = "",
    hints: str = "",
    for_curation: bool = False,
    curation_schema: str = "",
    user_message: str = "",
) -> str:
    two_track = for_curation and should_use_two_track_workflow(user_message)
    if two_track:
        main = pick_main_destination(user_message) or ""
        transit = resolve_transit_area(main) or ""
        kto_xml = build_two_track_kto_xml(main, transit, user_message)
        theme = build_theme_prompt_block(user_message)
        parts = [
            GANGWON_AGENT_ROLE_TWO_TRACK,
            kto_xml,
            KTO_TWO_TRACK_OUTPUT_FORMAT,
            f"# ROUTE CONTEXT\n- main_destination: {region_short_name(main)}\n- transit_area: {region_short_name(transit)} (인구감소·상생 경유지)",
        ]
        if theme:
            parts.append(theme)
    else:
        kto_xml = build_kto_data_xml(user_message)
        parts = [GANGWON_AGENT_ROLE, kto_xml, KTO_OUTPUT_FORMAT]
        if for_curation and user_message.strip():
            focus = region_focus_prompt_block(user_message)
            if focus:
                parts.append(focus)
    if hints:
        parts.append(hints)
    if for_curation and curation_schema:
        parts.append(curation_schema)
    elif catalog and not for_curation:
        parts.append(f"# GANGWON SPOT CATALOG (name|region|theme)\n{catalog}")
    return "\n\n".join(parts)
