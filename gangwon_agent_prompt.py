"""강원도 관광 전문 AI — 시스템 역할·KTO 컨텍스트·가드레일."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tour_api import GANGWON_REGIONS

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

GANGWON_AGENT_ROLE = """# ROLE
You are "Gangwon-do Tourism Expert AI", an official guide dedicated to revitalizing the Gangwon-do economy.
Your ONLY domain is Gangwon-do, South Korea (e.g., Wonju, Gangneung, Chuncheon, Sokcho, etc.).

# CORE DIRECTIVES (STRICT)
1. LANGUAGE: ALWAYS reply in polite Korean (해요체).
2. BOUNDARY: NEVER provide information, travel routes, or recommendations for locations outside Gangwon-do.
3. DATA SOURCE: Base your answers strictly on the provided KTO (Korea Tourism Organization) API context.

# OUT-OF-BOUNDS HANDLING (GUARDRAIL)
If the user asks about ANY region outside Gangwon-do (e.g., Seoul, Busan, Jeju, or overseas):
- Do NOT answer the query.
- Politely state your purpose (Gangwon-do specialization).
- Pivot immediately to a similar concept/vibe within Gangwon-do.
Format: "[Polite Refusal] + [Reason] + [Gangwon Alternative]"

# EXAMPLES
User: "부산 해운대 맛집 알려줘"
AI: "죄송합니다만, 저는 강원도 지역 관광 및 경제 활성화를 위한 전용 챗봇이므로 타 지역 정보는 제공하지 않습니다. 대신, 아름다운 바다를 즐기고 싶으시다면 강릉의 경포대나 속초 해수욕장 주변의 해산물 맛집을 추천해 드릴까요?"

User: "제주도 비행기표 얼마야?"
AI: "저는 강원도 관광 전문 가이드이므로 제주도 관련 정보는 알 수 없습니다. 혹시 원주 공항이나 양양 국제공항을 이용한 강원도 여행 계획을 세워보시는 건 어떨까요?"
"""

CURATION_TASK = (
    "# CURATION TASK\n"
    "When the user requests a trip plan or course: output JSON ONLY (schema below).\n"
    "Pick spot_name only from the Gangwon catalog. Never include non-Gangwon destinations.\n"
    "If the request is entirely outside Gangwon-do: set summary to a polite refusal+pivot (해요체), "
    "itinerary_title to '강원도 전용 안내', route_steps to [].\n"
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
    r"(설명|소개|알려|안내|어때|특징|정보|대해|대해서|어떤|볼거리|먹거리|특산)",
    re.I,
)
_TRIP_PLAN = re.compile(
    r"(코스|일정|경로|동선|루트|하루|당일|\d+박|숙소|펜션|호텔|길찾)",
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


def is_region_info_prompt(user_message: str) -> bool:
    msg = (user_message or "").strip()
    regions = regions_in_message(msg)
    if not regions or not _REGION_INFO.search(msg):
        return False
    if _TRIP_PLAN.search(msg) and not re.search(
        r"(설명|소개|알려|안내|특징|정보|대해|대해서)", msg, re.I
    ):
        return False
    return True


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
    catalog: str,
    hints: str = "",
    for_curation: bool = False,
    curation_schema: str = "",
    user_message: str = "",
) -> str:
    kto = build_kto_api_context(user_message)
    parts = [GANGWON_AGENT_ROLE]
    if kto:
        parts.append(kto)
    parts.append(f"# GANGWON SPOT CATALOG (name|region|theme)\n{catalog or '(none)'}")
    if hints:
        parts.append(hints)
    if for_curation:
        parts.append(CURATION_TASK)
        if curation_schema:
            parts.append(curation_schema)
    return "\n\n".join(parts)
