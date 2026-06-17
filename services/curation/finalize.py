"""Finalize Gemini/OpenAI JSON into curated trip results."""

from __future__ import annotations

from typing import Any

from gangwon_agent_prompt import (
    KTO_FALLBACK_INTRO,
    detect_trip_duration,
    pick_main_destination,
    pick_province_wide_spots,
    pick_regional_spots,
    regions_in_message,
    resolve_transit_area,
)
from services.curation.formatters import format_itinerary_message
from services.curation.matching import spots_from_names, steps_for_spots


def finalize_kto_json_curation(
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
        route_steps = steps_for_spots(curated, parsed) if curated else []
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
    curated = spots_from_names(spots, names, regions=regions or None)
    if not curated and regions:
        curated = pick_regional_spots(spots, regions, limit=min(3, max(len(names), 2)))
    if not curated and names:
        curated = spots_from_names(spots, names, regions=None)
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
    return {
        "itinerary_title": title,
        "summary": intro,
        "message": format_itinerary_message(legacy, curated),
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


def _build_option_from_parsed(
    opt: dict[str, Any] | None,
    spots: list[dict[str, Any]],
    regions_hint: list[str] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not opt:
        return [], []

    if opt.get("days"):
        route_steps: list[dict[str, Any]] = []
        curated: list[dict[str, Any]] = []
        order = 1
        for day_block in opt.get("days") or []:
            day_num = int(day_block.get("day") or 1)
            for item in day_block.get("schedule") or []:
                name = str(item.get("spot_name") or "").strip()
                if not name:
                    continue
                hits = spots_from_names(spots, [name], regions=regions_hint)
                if not hits:
                    hits = spots_from_names(spots, [name], regions=None)
                if not hits and regions_hint:
                    hits = pick_regional_spots(spots, regions_hint, limit=1)
                spot = hits[0] if hits else {
                    "name": name,
                    "region": (regions_hint or [""])[0],
                    "theme": "맛집" if "식사" in str(item.get("time_slot") or "") else "관광",
                    "description": str(item.get("description") or name),
                    "lat": 37.5,
                    "lng": 128.0,
                }
                if spot not in curated:
                    curated.append(spot)
                slot = str(item.get("time_slot") or "").strip()
                desc = str(item.get("description") or "").strip()
                route_steps.append(
                    {
                        "order": order,
                        "day": day_num,
                        "spot_name": spot["name"],
                        "region": spot.get("region", ""),
                        "theme": spot.get("theme", ""),
                        "stay_minutes": 75 if "식사" in slot else 60,
                        "why": f"[{slot}] {desc}".strip() if slot else desc,
                        "move_to_next": "",
                    }
                )
                order += 1
        return curated, route_steps

    itinerary = opt.get("itinerary") or []
    names = [str(item.get("spot_name") or "") for item in itinerary if item.get("spot_name")]
    curated = spots_from_names(spots, names, regions=regions_hint)
    if not curated and names:
        curated = spots_from_names(spots, names, regions=None)
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


def finalize_two_track_curation(
    parsed: dict[str, Any],
    spots: list[dict[str, Any]],
    user_message: str,
) -> dict[str, Any]:
    main = pick_main_destination(user_message) or ""
    transit = resolve_transit_area(main) or ""
    intro = str(parsed.get("intro") or parsed.get("introduction") or "")

    main_regions = [main] if main else None
    hybrid_regions = [r for r in [transit, main] if r] or None
    curated_1, steps_1 = _build_option_from_parsed(parsed.get("option_1"), spots, main_regions)
    curated_2, steps_2 = _build_option_from_parsed(parsed.get("option_2"), spots, hybrid_regions)

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
    duration_label = str(parsed.get("duration_detected") or detect_trip_duration(user_message).get("label", ""))
    title = (
        f"{main.rstrip('시군')} {duration_label} · 2가지 코스" if main else f"강원도 {duration_label} · 2가지 코스"
    )

    def day_plans_from_opt(opt: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "day": d.get("day"),
                "title": f"Day {d.get('day')}",
                "focus": " · ".join(
                    str(s.get("time_slot") or "") for s in (d.get("schedule") or []) if s.get("time_slot")
                ),
            }
            for d in (opt.get("days") or [])
        ]

    return {
        "itinerary_title": title,
        "summary": intro,
        "message": "\n".join(lines).strip(),
        "curated_spots": active_curated,
        "route_steps": active_steps,
        "map_tip": "지도에서 번호 순으로 동선을 확인하세요." if active_steps else "",
        "total_duration": duration_label or ("반나절~당일" if active_steps else ""),
        "trip_intent": {"duration": duration_label},
        "transit_plan": {},
        "accommodation": {},
        "day_plans": day_plans_from_opt(opt2 if active_steps == steps_2 else opt1),
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


def finalize_curation(parsed: dict[str, Any], spots: list[dict[str, Any]], user_message: str = "") -> dict[str, Any]:
    if parsed.get("option_1") is not None or parsed.get("option_2") is not None:
        return finalize_two_track_curation(parsed, spots, user_message)

    if (
        parsed.get("fallback_triggered") is not None
        or "introduction" in parsed
        or "itinerary" in parsed
    ):
        return finalize_kto_json_curation(parsed, spots, user_message)

    regions = regions_in_message(user_message)
    route_names = parsed.get("route_order") or parsed.get("recommended_spots") or []
    if not route_names:
        route_names = [
            s.get("spot_name")
            for s in (parsed.get("route_steps") or [])
            if s.get("spot_name")
        ]
    rec_names = parsed.get("recommended_spots") or route_names
    curated = spots_from_names(
        spots,
        list(route_names) if route_names else list(rec_names),
        regions=regions or None,
    )
    if not curated and rec_names:
        curated = spots_from_names(spots, list(rec_names), regions=regions or None)

    steps = steps_for_spots(curated, parsed)
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
