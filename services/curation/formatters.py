"""Itinerary message formatting."""

from __future__ import annotations

import re
from typing import Any

from services.curation.matching import steps_for_spots


def format_itinerary_message(parsed: dict[str, Any], curated: list[dict[str, Any]]) -> str:
    if not curated:
        return parsed.get("message") or parsed.get("summary") or "조건에 맞는 코스를 찾지 못했어요. 필터를 넓혀 다시 질문해 주세요."

    title = parsed.get("itinerary_title") or "🥔 오늘의 강원도 코스"
    summary = parsed.get("summary", "")
    steps = steps_for_spots(curated, parsed)
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
