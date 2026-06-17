import json
import os
import re
from typing import Any

import config  # noqa: F401 — .env 로드

from gangwon_agent_prompt import (
    KTO_FALLBACK_INTRO,
    build_agent_system_prompt,
    build_region_info_reply,
    collect_kto_catalog_entries,
    has_trip_plan_intent,
    is_multi_intent_prompt,
    is_region_info_only_prompt,
    out_of_gangwon_reply,
    pick_main_destination,
    pick_province_wide_spots,
    pick_regional_spots,
    region_empty_fallback_message,
    regions_in_message,
    resolve_kto_spot_by_name,
    resolve_transit_area,
)
from trip_intent import attach_origin_step, build_trip_hints, detect_themes, needs_ai_curation

MAX_SPOTS_IN_PROMPT = 12
MAX_HISTORY_MSGS = 0
MAX_HISTORY_CHARS = 200
MAX_USER_CHARS = 600

# KTO JSON schema is embedded in gangwon_agent_prompt.KTO_OUTPUT_FORMAT
CURATION_SCHEMA = ""


def _compact_spot_catalog(spots: list[dict[str, Any]], user_message: str = "") -> str:
    if not spots:
        return ""
    pool = spots
    msg = user_message.strip()
    regions = regions_in_message(msg) if msg else []
    if regions:
        regional = [s for s in spots if s.get("region") in regions]
        if regional:
            pool = regional
        else:
            kto_lines = []
            for region in regions:
                for entry in collect_kto_catalog_entries(region):
                    kto_lines.append(f"{entry['name']}|{region}|{entry['theme']}")
            return "\n".join(kto_lines[:MAX_SPOTS_IN_PROMPT])
    if msg:
        kws = [w for w in re.split(r"\s+", msg) if len(w) >= 2]
        for r in regions:
            kws.extend([r, r.replace("시", "").replace("군", "")])
        kws = list(dict.fromkeys(kws))
        themes = detect_themes(msg)
        theme_kws = list(themes)
        if "바다" in themes:
            theme_kws.extend(("해변", "해수욕", "서핑", "바다"))
        if kws or theme_kws:
            ranked: list[tuple[int, dict[str, Any]]] = []
            for s in pool:
                blob = f"{s['name']} {s['region']} {s['theme']} {s.get('description', '')}"
                score = sum(1 for kw in kws if kw in blob)
                score += sum(2 for kw in theme_kws if kw in blob)
                ranked.append((score, s))
            ranked.sort(key=lambda x: (-x[0], x[1]["name"]))
            matched = [s for sc, s in ranked if sc > 0][:MAX_SPOTS_IN_PROMPT]
            if matched:
                pool = matched
            elif not regions:
                pool = [s for _, s in ranked][:MAX_SPOTS_IN_PROMPT]
    return "\n".join(f"{s['name']}|{s['region']}|{s['theme']}" for s in pool[:MAX_SPOTS_IN_PROMPT])


def _build_system_prompt(
    spots: list[dict[str, Any]],
    for_curation: bool = False,
    user_message: str = "",
) -> str:
    catalog = "" if for_curation else _compact_spot_catalog(spots, user_message)
    hints = build_trip_hints(user_message) if user_message.strip() else ""
    return build_agent_system_prompt(
        catalog=catalog,
        hints=hints,
        for_curation=for_curation,
        curation_schema=CURATION_SCHEMA if for_curation else "",
        user_message=user_message,
    )


def _spots_from_names(
    spots: list[dict[str, Any]],
    names: list[str],
    *,
    regions: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not names:
        return []
    pool = spots
    if regions:
        pool = [s for s in spots if s.get("region") in regions]
    order = {name: idx for idx, name in enumerate(names)}
    by_name = {s["name"]: s for s in pool}
    result: list[dict[str, Any]] = []
    for name in names:
        if name in by_name and by_name[name] not in result:
            result.append(by_name[name])
    if not result:
        for spot in pool:
            for name in names:
                if name in spot["name"] or spot["name"] in name:
                    if spot not in result:
                        result.append(spot)
    if not result:
        for name in names:
            kto = resolve_kto_spot_by_name(name, regions)
            if not kto:
                kto = resolve_kto_spot_by_name(name, None)
            if kto and kto not in result:
                result.append(kto)
    if not result and regions:
        kto_pool = pick_regional_spots(spots, regions, limit=8)
        for name in names:
            for spot in kto_pool:
                if name in spot["name"] or spot["name"] in name:
                    if spot not in result:
                        result.append(spot)
        if not result:
            result = kto_pool[: min(len(names), 4)]
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
    if regions_in_message(user_message) and has_trip_plan_intent(user_message):
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
    regions = regions_in_message(user_message)
    picks = pick_regional_spots(spots, regions, limit=3) if regions else spots[:3]

    if not picks and regions:
        msg = region_empty_fallback_message()
        return {
            "itinerary_title": f"{regions[0]} 안내",
            "summary": msg,
            "message": msg,
            "recommended_spots": [],
            "route_order": [],
            "route_steps": [],
            "total_duration": "",
            "map_tip": "",
            "curated_spots": [],
            "source": source,
        }

    if not picks:
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
    for r in regions:
        keywords.extend([r, r.replace("시", "").replace("군", "")])
    candidates = picks
    ranked = []
    for spot in candidates:
        score = sum(1 for kw in keywords if kw and kw in f"{spot['name']} {spot['region']} {spot['theme']} {spot['description']}")
        ranked.append((score, spot))
    ranked.sort(key=lambda x: (-x[0], x[1]["name"]))
    picks = [spot for _, spot in ranked[:3]]
    region_label = regions[0] if regions else (picks[0]["region"] if picks else "")
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
        "itinerary_title": f"{region_label} 맞춤 코스" if region_label else "🥔 로컬 추천 코스",
        "summary": (
            f"{region_label} 중심 · 입력하신 키워드와 맞는 명소를 순서대로 묶었어요."
            if region_label
            else "입력하신 키워드와 가장 잘 맞는 강원도 명소를 순서대로 묶었어요."
        ),
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


def _finalize_kto_json_curation(
    parsed: dict[str, Any],
    spots: list[dict[str, Any]],
    user_message: str,
) -> dict[str, Any]:
    regions = regions_in_message(user_message)
    intro = str(parsed.get("introduction") or KTO_FALLBACK_INTRO)
    if not regions:
        regions = regions_in_message(intro)
    title = f"{regions[0]} AI 추천 코스" if regions else "강원도 AI 추천 코스"

    if parsed.get("fallback_triggered"):
        curated = pick_regional_spots(spots, regions, limit=3) if regions else pick_province_wide_spots(spots, limit=3)
        route_steps = _steps_for_spots(curated, parsed) if curated else []
        return {
            "itinerary_title": f"{regions[0]} 안내" if regions else "강원도 안내",
            "summary": intro,
            "message": format_itinerary_message({"itinerary_title": title, "summary": intro}, curated) if curated else intro,
            "curated_spots": curated,
            "route_steps": route_steps,
            "map_tip": "지도에서 번호 순으로 동선을 확인하세요." if curated else "",
            "total_duration": "반나절~당일" if curated else "",
            "trip_intent": {},
            "transit_plan": {},
            "accommodation": {},
            "day_plans": [],
            "source": "",
        }

    itinerary = parsed.get("itinerary") or []
    names = [str(item.get("spot_name") or "") for item in itinerary if item.get("spot_name")]
    curated = _spots_from_names(spots, names, regions=regions or None)
    if not curated and regions:
        curated = pick_regional_spots(spots, regions, limit=min(3, max(len(names), 2)))
    if not curated and names:
        curated = _spots_from_names(spots, names, regions=None)
    if not curated:
        curated = pick_regional_spots(spots, regions, limit=3) if regions else pick_province_wide_spots(spots, limit=3)

    by_name = {item.get("spot_name"): item for item in itinerary}
    route_steps = []
    for idx, spot in enumerate(curated, start=1):
        item = by_name.get(spot["name"], {})
        route_steps.append(
            {
                "order": item.get("step") or idx,
                "day": 1,
                "spot_name": spot["name"],
                "region": spot["region"],
                "theme": spot["theme"],
                "stay_minutes": 60,
                "why": (item.get("reason") or spot.get("description", "")).strip(),
                "move_to_next": "",
            }
        )

    legacy = {
        "itinerary_title": title,
        "summary": intro,
        "route_steps": route_steps,
        "total_duration": "반나절~당일",
        "map_tip": "지도에서 번호 순으로 동선을 확인하세요.",
    }
    message = format_itinerary_message(legacy, curated)
    return {
        "itinerary_title": title,
        "summary": intro,
        "message": message,
        "curated_spots": curated,
        "route_steps": route_steps,
        "map_tip": legacy["map_tip"],
        "total_duration": legacy["total_duration"],
        "trip_intent": {},
        "transit_plan": {},
        "accommodation": {},
        "day_plans": [],
        "source": "",
    }


def _finalize_two_track_curation(
    parsed: dict[str, Any],
    spots: list[dict[str, Any]],
    user_message: str,
) -> dict[str, Any]:
    main = pick_main_destination(user_message) or ""
    transit = resolve_transit_area(main) or ""
    intro = str(parsed.get("intro") or parsed.get("introduction") or "")

    def build_option(opt: dict[str, Any] | None, regions_hint: list[str] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if not opt:
            return [], []
        itinerary = opt.get("itinerary") or []
        names = [str(item.get("spot_name") or "") for item in itinerary if item.get("spot_name")]
        curated = _spots_from_names(spots, names, regions=regions_hint)
        if not curated and names:
            curated = _spots_from_names(spots, names, regions=None)
        if not curated and regions_hint:
            curated = pick_regional_spots(spots, regions_hint, limit=min(3, max(len(names), 2)))
        by_name = {item.get("spot_name"): item for item in itinerary}
        route_steps = []
        for idx, spot in enumerate(curated, start=1):
            item = by_name.get(spot["name"], {})
            for name in names:
                if name in spot["name"] or spot["name"] in name:
                    item = by_name.get(name, item)
                    break
            route_steps.append(
                {
                    "order": item.get("step") or idx,
                    "day": 1,
                    "spot_name": spot["name"],
                    "region": spot["region"],
                    "theme": spot["theme"],
                    "stay_minutes": 60,
                    "why": (item.get("reason") or spot.get("description", "")).strip(),
                    "move_to_next": "",
                }
            )
        return curated, route_steps

    main_regions = [main] if main else None
    hybrid_regions = [r for r in [transit, main] if r] or None
    curated_1, steps_1 = build_option(parsed.get("option_1"), main_regions)
    curated_2, steps_2 = build_option(parsed.get("option_2"), hybrid_regions)

    if parsed.get("option_2", {}).get("storytelling") and steps_2:
        steps_2[0]["why"] = f"{parsed['option_2']['storytelling']} {steps_2[0]['why']}".strip()

    lines = [intro, ""]
    opt1 = parsed.get("option_1") or {}
    opt2 = parsed.get("option_2") or {}
    if curated_1:
        lines.append(f"## {opt1.get('title', '1안')}")
        lines.append(" → ".join(s["spot_name"] for s in steps_1))
        lines.append("")
    if curated_2:
        lines.append(f"## {opt2.get('title', '2안')}")
        if opt2.get("storytelling"):
            lines.append(opt2["storytelling"])
        lines.append(" → ".join(s["spot_name"] for s in steps_2))

    active_curated = curated_2 or curated_1
    active_steps = steps_2 or steps_1
    title = f"{main.rstrip('시군')} 여행 2가지 코스" if main else "강원도 여행 2가지 코스"

    return {
        "itinerary_title": title,
        "summary": intro,
        "message": "\n".join(lines).strip(),
        "curated_spots": active_curated,
        "route_steps": active_steps,
        "map_tip": "지도에서 번호 순으로 동선을 확인하세요." if active_steps else "",
        "total_duration": "반나절~당일" if active_steps else "",
        "trip_intent": {},
        "transit_plan": {},
        "accommodation": {},
        "day_plans": [],
        "course_options": [
            {
                "key": "option_1",
                "title": opt1.get("title", "1안: 목적지 집중 코스"),
                "summary": "",
                "route_steps": steps_1,
                "curated_spots": curated_1,
            },
            {
                "key": "option_2",
                "title": opt2.get("title", "2안: 지역 상생 하이브리드 코스"),
                "summary": opt2.get("storytelling", ""),
                "route_steps": steps_2,
                "curated_spots": curated_2,
            },
        ],
        "active_course_option": "option_2" if curated_2 else "option_1",
        "source": "",
    }


def _finalize_curation(parsed: dict[str, Any], spots: list[dict[str, Any]], user_message: str = "") -> dict[str, Any]:
    if parsed.get("option_1") is not None or parsed.get("option_2") is not None:
        return _finalize_two_track_curation(parsed, spots, user_message)

    if (
        parsed.get("fallback_triggered") is not None
        or "introduction" in parsed
        or "itinerary" in parsed
    ):
        return _finalize_kto_json_curation(parsed, spots, user_message)

    regions = regions_in_message(user_message)
    route_names = parsed.get("route_order") or parsed.get("recommended_spots") or []
    if not route_names:
        route_names = [
            s.get("spot_name")
            for s in (parsed.get("route_steps") or [])
            if s.get("spot_name")
        ]
    rec_names = parsed.get("recommended_spots") or route_names
    curated = _spots_from_names(
        spots,
        list(route_names) if route_names else list(rec_names),
        regions=regions or None,
    )
    if not curated and rec_names:
        curated = _spots_from_names(spots, list(rec_names), regions=regions or None)

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


def _maybe_prepend_region_intro(
    user_message: str,
    spots: list[dict[str, Any]],
    result: dict[str, Any],
) -> dict[str, Any]:
    if not is_multi_intent_prompt(user_message):
        return result
    if result.get("source") in ("gemini", "openai"):
        return result
    if not result.get("route_steps") and not result.get("curated_spots"):
        return result
    intro = build_region_info_reply(user_message, spots)
    body = result.get("message") or result.get("summary") or ""
    if intro and intro not in body:
        result["message"] = f"{intro}\n\n{body}".strip()
        if not result.get("summary"):
            result["summary"] = intro
    return result


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

    if is_region_info_only_prompt(user_message):
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
        return _maybe_prepend_region_intro(user_message, spots, _fallback_curation(user_message, spots, source="local_skip"))

    complex = needs_ai_curation(user_message)
    if provider == "google" and not os.getenv("GOOGLE_API_KEY"):
        if complex:
            return _ai_required_failure(user_message, "AI 키가 설정되지 않았습니다.")
        return _maybe_prepend_region_intro(user_message, spots, _fallback_curation(user_message, spots, source="local"))
    if provider != "google" and not os.getenv("OPENAI_API_KEY"):
        if complex:
            return _ai_required_failure(user_message, "AI 키가 설정되지 않았습니다.")
        return _maybe_prepend_region_intro(user_message, spots, _fallback_curation(user_message, spots, source="local"))

    parsed: dict[str, Any] | None = None
    ai_source = "gemini" if provider == "google" else "openai"
    if provider == "google":
        parsed = _call_google_curation(user_message, spots, history)
    else:
        parsed = _call_openai_curation(user_message, spots, history)

    if not parsed:
        if complex:
            return _ai_required_failure(user_message)
        return _maybe_prepend_region_intro(user_message, spots, _fallback_curation(user_message, spots, source="local_api_fail"))

    result = _finalize_curation(parsed, spots, user_message)
    if not result["curated_spots"]:
        if complex:
            return _ai_required_failure(user_message, "AI 응답에서 장소를 찾지 못했습니다.")
        return _maybe_prepend_region_intro(user_message, spots, _fallback_curation(user_message, spots, source="local_api_fail"))
    result["route_steps"] = attach_origin_step(
        result["route_steps"],
        result.get("trip_intent"),
        result.get("transit_plan"),
        user_message,
    )
    result["source"] = ai_source
    if is_multi_intent_prompt(user_message) and ai_source not in ("gemini", "openai"):
        intro = build_region_info_reply(user_message, spots)
        body = result.get("message") or ""
        if intro and intro not in body:
            result["message"] = f"{intro}\n\n{body}".strip()
            if not result.get("summary"):
                result["summary"] = intro
    return result
