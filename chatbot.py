import json
import os
import re
from typing import Any

import config  # noqa: F401 — .env 로드

CURATION_SCHEMA_HINT = """
반드시 아래 JSON만 출력하세요(다른 텍스트 금지):
{
  "message": "사용자에게 보여줄 한국어 답변(이유 2가지 + 동선 팁 포함)",
  "recommended_spots": ["DB에 있는 정확한 장소명", "..."],
  "route_order": ["방문 순서대로 장소명"],
  "map_tip": "지도에서 보기 좋은 한 줄 동선 설명"
}
recommended_spots는 제공된 DB 장소명만 사용하고 1~3개 선택하세요.
route_order는 recommended_spots의 방문 순서입니다.
""".strip()


def _build_system_prompt(spots: list[dict[str, Any]], for_curation: bool = False) -> str:
    spot_lines = "\n".join(
        [
            f"- {s['name']} ({s['region']}, {s['theme']}, lat={s['lat']}, lng={s['lng']}): {s['description']}"
            for s in spots[:20]
        ]
    )
    base = f"""
당신은 강원도 인구 감소 지역 여행 큐레이터입니다.
사용자 취향에 맞춰 과도하게 유명하지 않은 장소를 추천합니다.
답변은 반드시 한국어로, 짧고 실용적으로 작성하세요.

현재 앱 DB 후보지(이름을 정확히 사용):
{spot_lines if spot_lines else "- 현재 필터 조건에 맞는 후보지가 없습니다."}
""".strip()
    if for_curation:
        return f"{base}\n\n{CURATION_SCHEMA_HINT}"
    return (
        f"{base}\n"
        "추천 시 이유 2가지와 이동 동선 팁 1가지를 포함하세요."
    )


def _spots_from_names(spots: list[dict[str, Any]], names: list[str]) -> list[dict[str, Any]]:
    if not names:
        return []
    order = {name: idx for idx, name in enumerate(names)}
    by_name = {s["name"]: s for s in spots}
    result = []
    for name in names:
        if name in by_name and by_name[name] not in result:
            result.append(by_name[name])
    if result:
        return result
    for spot in spots:
        for name in names:
            if name in spot["name"] or spot["name"] in name:
                if spot not in result:
                    result.append(spot)
    result.sort(key=lambda s: order.get(s["name"], 999))
    return result[:3]


def _parse_curation_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None
    return None


def _fallback_curation(user_message: str, spots: list[dict[str, Any]]) -> dict[str, Any]:
    if not spots:
        return {
            "message": "현재 조건에 맞는 장소가 없어요. 지역/테마 필터를 조금 넓혀 다시 시도해 주세요.",
            "recommended_spots": [],
            "route_order": [],
            "map_tip": "",
        }

    keywords = user_message.replace(",", " ").split()
    ranked = []
    for spot in spots:
        score = 0
        text = f"{spot['name']} {spot['region']} {spot['theme']} {spot['description']}"
        for kw in keywords:
            if kw and kw in text:
                score += 1
        ranked.append((score, spot))

    ranked.sort(key=lambda x: (-x[0], x[1]["region"]))
    picks = [spot for _, spot in ranked[:3]]
    names = [s["name"] for s in picks]
    lines = [
        "AI 키가 없어 로컬 추천 로직으로 안내드려요.",
        "",
        "추천 장소:",
    ]
    for idx, spot in enumerate(picks, start=1):
        lines.append(f"{idx}. {spot['name']} ({spot['region']}) - {spot['description']}")
    lines.append("")
    lines.append("동선 팁: 같은 군/시 기준으로 묶어 방문하면 이동 시간이 줄어듭니다.")
    return {
        "message": "\n".join(lines),
        "recommended_spots": names,
        "route_order": names,
        "map_tip": "왼쪽 지도에서 번호 순서대로 동선을 확인해 보세요.",
    }


def _call_openai_curation(
    user_message: str,
    spots: list[dict[str, Any]],
    chat_history: list[dict[str, str]],
) -> dict[str, Any] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        messages = [{"role": "system", "content": _build_system_prompt(spots, for_curation=True)}]
        messages.extend(chat_history[-8:])
        messages.append({"role": "user", "content": user_message})
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.5,
            response_format={"type": "json_object"},
        )
        raw = (response.choices[0].message.content or "").strip()
        return _parse_curation_json(raw)
    except Exception:
        return None


def _call_google_curation(
    user_message: str,
    spots: list[dict[str, Any]],
    chat_history: list[dict[str, str]],
) -> dict[str, Any] | None:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model_name = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
        model = genai.GenerativeModel(model_name)
        context = "\n".join([f"{m['role']}: {m['content']}" for m in chat_history[-6:]])
        prompt = (
            f"{_build_system_prompt(spots, for_curation=True)}\n\n"
            f"대화기록:\n{context}\n\n사용자 질문:\n{user_message}"
        )
        response = model.generate_content(prompt)
        return _parse_curation_json((response.text or "").strip())
    except Exception:
        return None


def curate_trip(
    user_message: str,
    spots: list[dict[str, Any]],
    chat_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """프롬프트 → AI 큐레이션 → 지도용 장소 목록."""
    history = chat_history or []
    provider = os.getenv("AI_PROVIDER", "openai").lower()

    parsed: dict[str, Any] | None = None
    if provider == "google":
        parsed = _call_google_curation(user_message, spots, history)
    else:
        parsed = _call_openai_curation(user_message, spots, history)

    if not parsed:
        parsed = _fallback_curation(user_message, spots)

    route_names = parsed.get("route_order") or parsed.get("recommended_spots") or []
    rec_names = parsed.get("recommended_spots") or route_names
    curated = _spots_from_names(spots, list(route_names) if route_names else list(rec_names))
    if not curated and rec_names:
        curated = _spots_from_names(spots, list(rec_names))

    return {
        "message": parsed.get("message", "").strip() or "추천을 생성하지 못했어요. 다시 질문해 주세요.",
        "curated_spots": curated,
        "map_tip": parsed.get("map_tip", "").strip(),
    }


def generate_reply(
    user_message: str,
    spots: list[dict[str, Any]],
    chat_history: list[dict[str, str]] | None = None,
) -> str:
    return curate_trip(user_message, spots, chat_history)["message"]
