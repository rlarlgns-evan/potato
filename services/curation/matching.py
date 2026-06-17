"""Spot name matching for curation results."""

from __future__ import annotations

from typing import Any

from gangwon_agent_prompt import pick_regional_spots, resolve_kto_spot_by_name


def spots_from_names(
    spots: list[dict[str, Any]],
    names: list[str],
    *,
    regions: list[str] | None = None,
    strict_regions: bool = True,
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
            if not kto and not strict_regions and not regions:
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


def steps_for_spots(curated: list[dict[str, Any]], parsed: dict[str, Any]) -> list[dict[str, Any]]:
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
