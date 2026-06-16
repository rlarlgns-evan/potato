import json
import os
import re
from typing import Any

import config  # noqa: F401 — .env 로드

from gangwon_agent_prompt import (
    build_agent_system_prompt,
    build_region_info_reply,
    is_region_info_prompt,
    out_of_gangwon_reply,
    regions_in_message,
)
from trip_intent import attach_origin_step, build_trip_hints, detect_themes, needs_ai_curation

MAX_SPOTS_IN_PROMPT = 12
MAX_HISTORY_MSGS = 0
MAX_HISTORY_CHARS = 200
MAX_USER_CHARS = 600

# English instructions → fewer tokens; user-facing JSON values stay Korean.
CURATION_SCHEMA = (
    "JSON only.Korean brief.why≤80chars. "
    "Extract trip_intent from user: origin,transport,duration,companion,themes. "
    "If origin/transport/lodging/duration given: plan outbound transit, lodging area, return. "
    '{"trip_intent":{"origin":"","transport":"","duration":"","companion":"","themes":[]},'
    '"transit_plan":{"outbound":"","return":"","local_transit":""},'
    '"accommodation":{"area":"","type":"","note":""},'
    '"itinerary_title":"","summary":"","total_duration":"",'
    '"day_plans":[{"day":1,"title":"","focus":""}],'
    '"route_steps":[{"order":1,"day":1,"spot_name":"","stay_minutes":60,"why":"","move_to_next":""}],'
    '"map_tip":""}. '
    "1박2일=2-4 spots across days; spot_name exact from catalog; "
    "move_to_next must include KTX/버스/환승 when public transit; "
    "accommodation.area near evening spot cluster."
)


def _compact_spot_catalog(spots: list[dict[str, Any]], user_message: str = "") -> str:
    if not spots:
        return ""
    pool = spots
    msg = user_message.strip()
    if msg:
        kws = [w for w in re.split(r"\s+", msg) if len(w) >= 2]
        themes = detect_themes(msg)
        theme_kws = list(themes)
        if "바다" in themes:
            theme_kws.extend(("해변", "해수욕", "서핑", "바다"))
        if kws or theme_kws:
            ranked: list[tuple[int, dict[str, Any]]] = []
            for s in spots:
                blob = f"{s['name']} {s['region']} {s['theme']} {s.get('description', '')}"
                score = sum(1 for kw in kws if kw in blob)
                score += sum(2 for kw in theme_kws if kw in blob)
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
    hints = build_trip_hints(user_message) if user_message.strip() else ""
    return build_agent_system_prompt(
        catalog=catalog,
        hints=hints,
        for_curation=for_curation,
        curation_schema=CURATION_SCHEMA if for_curation else "",
        user_message=user_message,
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
                "day": step.get("day") or 1,
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
    trip_intent = parsed.get("trip_intent") or {}
    transit = parsed.get("transit_plan") or {}
    lodging = parsed.get("accommodation") or {}
    day_plans = parsed.get("day_plans") or []

    lines = [f"## {title}", ""]
    if summary:
        lines.extend([summary, ""])

    if trip_intent:
        origin = trip_intent.get("origin", "")
        transport = trip_intent.get("transport", "")
        dur = trip_intent.get("duration", "") or duration
        companion = trip_intent.get("companion", "")
        themes = trip_intent.get("themes") or []
        if origin or transport or dur or companion or themes:
            lines.append("### 🧭 여행 조건")
            if origin:
                lines.append(f"- **출발:** {origin}")
            if transport:
                lines.append(f"- **이동:** {transport}")
            if dur:
                lines.append(f"- **일정:** {dur}")
            if companion:
                lines.append(f"- **동행:** {companion}")
            if themes:
                lines.append(f"- **테마:** {', '.join(themes)}")
            lines.append("")

    if transit and any(transit.get(k) for k in ("outbound", "return", "local_transit")):
        lines.append("### 🚆 이동 경로")
        if transit.get("outbound"):
            lines.append(f"- **가는 길:** {transit['outbound']}")
        if transit.get("local_transit"):
            lines.append(f"- **현지 이동:** {transit['local_transit']}")
        if transit.get("return"):
            lines.append(f"- **오는 길:** {transit['return']}")
        lines.append("")

    if lodging and any(lodging.get(k) for k in ("area", "type", "note")):
        lines.append("### 🏨 숙소")
        area = lodging.get("area", "")
        typ = lodging.get("type", "")
        note = lodging.get("note", "")
        if area or typ:
            lines.append(f"- **추천:** {area} {typ}".strip())
        if note:
            lines.append(f"- {note}")
        lines.append("")

    if day_plans:
        lines.append("### 📅 일정 개요")
        for dp in day_plans:
            day = dp.get("day", "")
            t = dp.get("title", "")
            focus = dp.get("focus", "")
            line = f"- **Day {day}** {t}".strip()
            if focus:
                line += f" — {focus}"
            lines.append(line)
        lines.append("")

    if duration and not trip_intent.get("duration"):
        lines.append(f"⏱ **예상 일정:** {duration}")
        lines.append("")
    lines.append("### 📍 방문 동선 (아래 지도 번호와 동일)")
    lines.append("")

    for step in steps:
        stay = step.get("stay_minutes")
        stay_txt = f" · 약 **{stay}분**" if stay else ""
        day_txt = f" · Day {step['day']}" if step.get("day") and step["day"] != 1 else ""
        lines.append(
            f"**{step['order']}. {step['spot_name']}** "
            f"({step['region']} · {step['theme']}){day_txt}{stay_txt}"
        )
        lines.append(f"- {step['why']}")
        if step.get("move_to_next"):
            icon = "🚆" if re.search(r"KTX|버스|열차|지하철|대중교통|역|터미널", step["move_to_next"]) else "🚗"
            lines.append(f"- {icon} **이동:** {step['move_to_next']}")
        lines.append("")

    if map_tip:
        lines.extend(["---", "### 🗺️ 지도에서 보기", map_tip, "", "👇 **다음 섹션**에서 카카오맵 주황 동선을 확인하세요."])

    return "\n".join(lines)


def _local_match_quality(user_message: str, spots: list[dict[str, Any]]) -> tuple[int, int, int]:
    """(top_score, strong_hit_count, top3_score_sum) — 높을수록 로컬만으로 충분."""
    kws = [w for w in re.split(r"\s+", user_message.replace(",", " ")) if len(w) >= 2]
    if not kws or not spots:
        return 0, 0, 0
    scores = sorted(
        (
            (
                sum(1 for kw in kws if kw in f"{s['name']} {s['region']} {s['theme']} {s['description']}"),
                s,
            )
            for s in spots
        ),
        key=lambda x: (-x[0], x[1]["name"]),
    )
    top = scores[0][0] if scores else 0
    strong = sum(1 for sc, _ in scores if sc >= 2)
    top3 = sum(sc for sc, _ in scores[:3])
    return top, strong, top3


def _should_call_ai(user_message: str, spots: list[dict[str, Any]]) -> bool:
    """복합 조건(출발·교통·숙박·기간)은 반드시 AI. 단순 키워드만 로컬."""
    if needs_ai_curation(user_message):
        return True
    top, strong, top3 = _local_match_quality(user_message, spots)
    if top >= 3:
        return False
    if top >= 2 and strong >= 2:
        return False
    if top3 >= 5:
        return False
    return True


def _ai_required_failure(user_message: str, reason: str = "") -> dict[str, Any]:
    detail = reason or "잠시 후 다시 시도하거나, 조건을 나눠서 질문해 보세요."
    message = (
        "출발·교통·숙박·기간 조건이 포함된 질문은 AI가 필요합니다. "
        f"{detail}"
    )
    return {
        "itinerary_title": "AI 일정 필요",
        "summary": "",
        "message": message,
        "curated_spots": [],
        "route_steps": [],
        "map_tip": "",
        "total_duration": "",
        "trip_intent": {},
        "transit_plan": {},
        "accommodation": {},
        "day_plans": [],
        "source": "ai_required_fail",
    }


def _fallback_curation(user_message: str, spots: list[dict[str, Any]], source: str = "local") -> dict[str, Any]:
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
    route_steps = _steps_for_spots(curated, parsed)
    route_steps = attach_origin_step(
        route_steps,
        parsed.get("trip_intent"),
        parsed.get("transit_plan"),
        user_message,
    )
    return {
        **parsed,
        "message": format_itinerary_message(parsed, curated),
        "curated_spots": curated,
        "route_steps": route_steps,
        "source": source,
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
        messages.append({"role": "user", "content": user_message[:MAX_USER_CHARS]})
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
        model_name = os.getenv("GOOGLE_MODEL", "gemini-3.5-flash")
        sys_prompt = _build_system_prompt(spots, for_curation=True, user_message=user_message)
        model = genai.GenerativeModel(model_name, system_instruction=sys_prompt)
        prompt_parts = [user_message[:MAX_USER_CHARS]]
        response = model.generate_content(
            "\n".join(prompt_parts),
            generation_config=genai.GenerationConfig(
                temperature=0.5,
                response_mime_type="application/json",
                max_output_tokens=4096,
            ),
        )
        return _parse_curation_json((response.text or "").strip())
    except Exception:
        return None


def _finalize_curation(parsed: dict[str, Any], spots: list[dict[str, Any]]) -> dict[str, Any]:
    route_names = parsed.get("route_order") or parsed.get("recommended_spots") or []
    if not route_names:
        route_names = [
            s.get("spot_name")
            for s in (parsed.get("route_steps") or [])
            if s.get("spot_name")
        ]
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
        "trip_intent": parsed.get("trip_intent") or {},
        "transit_plan": parsed.get("transit_plan") or {},
        "accommodation": parsed.get("accommodation") or {},
        "day_plans": parsed.get("day_plans") or [],
        "source": "",
    }


def curate_trip(
    user_message: str,
    spots: list[dict[str, Any]],
    chat_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    history = chat_history or []
    refusal = out_of_gangwon_reply(user_message)
    if refusal:
        return {
            "itinerary_title": "강원도 전용 안내",
            "summary": refusal,
            "message": refusal,
            "curated_spots": [],
            "route_steps": [],
            "source": "guardrail",
        }

    if is_region_info_prompt(user_message):
        reply = build_region_info_reply(user_message, spots)
        region = regions_in_message(user_message)
        title = f"{region[0]} 안내" if region else "지역 안내"
        return {
            "itinerary_title": title,
            "summary": reply,
            "message": reply,
            "curated_spots": [],
            "route_steps": [],
            "source": "local",
        }

    provider = os.getenv("AI_PROVIDER", "openai").lower()

    if not _should_call_ai(user_message, spots):
        return _fallback_curation(user_message, spots, source="local_skip")

    complex = needs_ai_curation(user_message)
    if provider == "google" and not os.getenv("GOOGLE_API_KEY"):
        if complex:
            return _ai_required_failure(user_message, "AI 키가 설정되지 않았습니다.")
        return _fallback_curation(user_message, spots, source="local")
    if provider != "google" and not os.getenv("OPENAI_API_KEY"):
        if complex:
            return _ai_required_failure(user_message, "AI 키가 설정되지 않았습니다.")
        return _fallback_curation(user_message, spots, source="local")

    parsed: dict[str, Any] | None = None
    ai_source = "gemini" if provider == "google" else "openai"
    if provider == "google":
        parsed = _call_google_curation(user_message, spots, history)
    else:
        parsed = _call_openai_curation(user_message, spots, history)

    if not parsed:
        if complex:
            return _ai_required_failure(user_message)
        return _fallback_curation(user_message, spots, source="local_api_fail")

    result = _finalize_curation(parsed, spots)
    if not result["curated_spots"]:
        if complex:
            return _ai_required_failure(user_message, "AI 응답에서 장소를 찾지 못했습니다.")
        return _fallback_curation(user_message, spots, source="local_api_fail")
    result["route_steps"] = attach_origin_step(
        result["route_steps"],
        result.get("trip_intent"),
        result.get("transit_plan"),
        user_message,
    )
    result["source"] = ai_source
    return result
