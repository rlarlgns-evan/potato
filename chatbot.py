import json
import os
import re
from typing import Any

import config  # noqa: F401 — .env 로드

MAX_SPOTS_IN_PROMPT = 28
MAX_HISTORY_MSGS = 2
MAX_HISTORY_CHARS = 350

# English instructions → fewer tokens; user-facing JSON values stay Korean.
CURATION_SCHEMA = (
    "Output JSON only. Fields itinerary_title, summary, why, move_to_next, "
    "total_duration, map_tip: Korean, brief. "
    '{"itinerary_title":"","summary":"","recommended_spots":[],"route_order":[],'
    '"route_steps":[{"order":1,"spot_name":"","stay_minutes":60,"why":"","move_to_next":""}],'
    '"total_duration":"","map_tip":""}. '
    "1-4 spots; spot_name must copy catalog names exactly; route_steps same order as route_order."
)


def _compact_spot_catalog(spots: list[dict[str, Any]], user_message: str = "") -> str:
    if not spots:
        return ""
    pool = spots
    msg = user_message.strip()
    if msg:
        kws = [w for w in re.split(r"\s+", msg) if len(w) >= 2]
        if kws:
            ranked: list[tuple[int, dict[str, Any]]] = []
            for s in spots:
                blob = f"{s['name']} {s['region']} {s['theme']}"
                score = sum(1 for kw in kws if kw in blob)
                ranked.append((score, s))
            ranked.sort(key=lambda x: (-x[0], x[1]["name"]))
            matched = [s for sc, s in ranked if sc > 0][:MAX_SPOTS_IN_PROMPT]
            pool = matched if len(matched) >= 6 else [s for _, s in ranked][:MAX_SPOTS_IN_PROMPT]
    return "\n".join(f"{s['name']}|{s['region']}|{s['theme']}" for s in pool[:MAX_SPOTS_IN_PROMPT])


def _build_system_prompt(
    spots: list[dict[str, Any]],
    for_curation: bool = False,
    user_message: str = "",
) -> str:
    catalog = _compact_spot_catalog(spots, user_message)
    base = (
        "Gangwon (Korea) trip planner. Pick spots from catalog; user text fields in Korean.\n"
        f"Catalog name|region|theme:\n{catalog or '(none)'}"
    )
    return f"{base}\n{CURATION_SCHEMA}" if for_curation else base


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
    return result[:4]


def _parse_curation_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
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


def _steps_for_spots(curated: list[dict[str, Any]], parsed: dict[str, Any]) -> list[dict[str, Any]]:
    raw_steps = parsed.get("route_steps") or []
    by_name = {s.get("spot_name"): s for s in raw_steps if s.get("spot_name")}
    steps = []
    for idx, spot in enumerate(curated, start=1):
        step = by_name.get(spot["name"], {})
        steps.append(
            {
                "order": idx,
                "spot_name": spot["name"],
                "region": spot["region"],
                "theme": spot["theme"],
                "stay_minutes": step.get("stay_minutes"),
                "why": (step.get("why") or spot["description"]).strip(),
                "move_to_next": (step.get("move_to_next") or "").strip(),
            }
        )
    return steps


def format_itinerary_message(parsed: dict[str, Any], curated: list[dict[str, Any]]) -> str:
    if not curated:
        return parsed.get("message") or parsed.get("summary") or "조건에 맞는 코스를 찾지 못했어요. 필터를 넓혀 다시 질문해 주세요."

    title = parsed.get("itinerary_title") or "🥔 오늘의 강원도 코스"
    summary = parsed.get("summary", "")
    steps = _steps_for_spots(curated, parsed)
    duration = parsed.get("total_duration", "")
    map_tip = parsed.get("map_tip", "")

    lines = [f"## {title}", ""]
    if summary:
        lines.extend([summary, ""])
    if duration:
        lines.append(f"⏱ **예상 일정:** {duration}")
        lines.append("")
    lines.append("### 📍 방문 동선 (아래 지도 번호와 동일)")
    lines.append("")

    for step in steps:
        stay = step.get("stay_minutes")
        stay_txt = f" · 약 **{stay}분**" if stay else ""
        lines.append(f"**{step['order']}. {step['spot_name']}** ({step['region']} · {step['theme']}){stay_txt}")
        lines.append(f"- {step['why']}")
        if step.get("move_to_next"):
            lines.append(f"- 🚗 **이동:** {step['move_to_next']}")
        lines.append("")

    if map_tip:
        lines.extend(["---", "### 🗺️ 지도에서 보기", map_tip, "", "👇 **다음 섹션**에서 카카오맵 주황 동선을 확인하세요."])

    return "\n".join(lines)


def _fallback_curation(user_message: str, spots: list[dict[str, Any]]) -> dict[str, Any]:
    if not spots:
        return {
            "itinerary_title": "후보 없음",
            "summary": "현재 필터에 맞는 장소가 없습니다.",
            "recommended_spots": [],
            "route_order": [],
            "route_steps": [],
            "total_duration": "",
            "map_tip": "",
        }

    keywords = user_message.replace(",", " ").split()
    ranked = []
    for spot in spots:
        score = sum(1 for kw in keywords if kw and kw in f"{spot['name']} {spot['region']} {spot['theme']} {spot['description']}")
        ranked.append((score, spot))
    ranked.sort(key=lambda x: (-x[0], x[1]["region"]))
    picks = [spot for _, spot in ranked[:3]]
    names = [s["name"] for s in picks]

    route_steps = []
    for idx, spot in enumerate(picks, start=1):
        move = ""
        if idx < len(picks):
            move = f"{spot['region']}에서 {picks[idx]['region']} 방향으로 이동 (군 내/인접 구간 묶어 이동)"
        route_steps.append(
            {
                "order": idx,
                "spot_name": spot["name"],
                "stay_minutes": 60,
                "why": spot["description"],
                "move_to_next": move,
            }
        )

    parsed = {
        "itinerary_title": "🥔 로컬 추천 코스",
        "summary": "입력하신 키워드와 가장 잘 맞는 강원도 명소를 순서대로 묶었어요.",
        "recommended_spots": names,
        "route_order": names,
        "route_steps": route_steps,
        "total_duration": "반나절~당일",
        "map_tip": "지도에서 1→2→3 번호 순으로 주황 동선을 따라가 보세요.",
    }
    curated = _spots_from_names(spots, names)
    return {
        **parsed,
        "message": format_itinerary_message(parsed, curated),
        "curated_spots": curated,
        "route_steps": _steps_for_spots(curated, parsed),
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
        messages = [
            {
                "role": "system",
                "content": _build_system_prompt(spots, for_curation=True, user_message=user_message),
            }
        ]
        for m in chat_history[-MAX_HISTORY_MSGS:]:
            if m["role"] in ("user", "assistant"):
                messages.append({"role": m["role"], "content": m["content"][:MAX_HISTORY_CHARS]})
        messages.append({"role": "user", "content": user_message[:800]})
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.5,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        return _parse_curation_json((response.choices[0].message.content or "").strip())
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
        model_name = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash-lite")
        sys_prompt = _build_system_prompt(spots, for_curation=True, user_message=user_message)
        model = genai.GenerativeModel(model_name, system_instruction=sys_prompt)
        prompt_parts = [user_message[:800]]
        hist = [m for m in chat_history[-MAX_HISTORY_MSGS:] if m["role"] in ("user", "assistant")]
        if hist:
            ctx = " | ".join(f"{m['role'][0]}:{m['content'][:MAX_HISTORY_CHARS]}" for m in hist)
            prompt_parts.insert(0, f"Context:{ctx}")
        response = model.generate_content(
            "\n".join(prompt_parts),
            generation_config=genai.GenerationConfig(
                temperature=0.5,
                response_mime_type="application/json",
                max_output_tokens=2048,
            ),
        )
        return _parse_curation_json((response.text or "").strip())
    except Exception:
        return None


def _finalize_curation(parsed: dict[str, Any], spots: list[dict[str, Any]]) -> dict[str, Any]:
    route_names = parsed.get("route_order") or parsed.get("recommended_spots") or []
    rec_names = parsed.get("recommended_spots") or route_names
    curated = _spots_from_names(spots, list(route_names) if route_names else list(rec_names))
    if not curated and rec_names:
        curated = _spots_from_names(spots, list(rec_names))

    steps = _steps_for_spots(curated, parsed)
    message = format_itinerary_message(parsed, curated)

    return {
        "itinerary_title": parsed.get("itinerary_title", "추천 코스"),
        "summary": parsed.get("summary", ""),
        "message": message,
        "curated_spots": curated,
        "route_steps": steps,
        "map_tip": parsed.get("map_tip", "").strip(),
        "total_duration": parsed.get("total_duration", ""),
    }


def curate_trip(
    user_message: str,
    spots: list[dict[str, Any]],
    chat_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    history = chat_history or []
    provider = os.getenv("AI_PROVIDER", "openai").lower()

    parsed: dict[str, Any] | None = None
    if provider == "google":
        parsed = _call_google_curation(user_message, spots, history)
    else:
        parsed = _call_openai_curation(user_message, spots, history)

    if not parsed:
        return _fallback_curation(user_message, spots)

    result = _finalize_curation(parsed, spots)
    if not result["curated_spots"]:
        return _fallback_curation(user_message, spots)
    return result


def generate_reply(
    user_message: str,
    spots: list[dict[str, Any]],
    chat_history: list[dict[str, str]] | None = None,
) -> str:
    return curate_trip(user_message, spots, chat_history)["message"]
