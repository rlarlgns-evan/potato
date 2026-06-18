"""Plan routes from KTO spot picks + Kakao Directions."""

from __future__ import annotations

from typing import Any

from gangwon_agent_prompt import pick_regional_spots, regions_in_message

from services.routing.kakao import LatLng, RoutePlan, fetch_kakao_directions, parse_kakao_route


def plan_route_for_spots(spots: list[dict[str, Any]]) -> RoutePlan | None:
    if len(spots) < 2:
        return None
    points = [
        LatLng(
            lng=float(s["lng"]),
            lat=float(s["lat"]),
            name=str(s.get("name") or ""),
        )
        for s in spots
        if s.get("lat") is not None and s.get("lng") is not None
    ]
    if len(points) < 2:
        return None
    try:
        raw = fetch_kakao_directions(points)
        return parse_kakao_route(spots[: len(points)], raw)
    except (RuntimeError, ValueError, OSError) as exc:
        import logging

        logging.getLogger(__name__).warning("Kakao route plan failed: %s", exc)
        return None


def plan_route_for_message(
    user_message: str,
    spots: list[dict[str, Any]],
    *,
    limit: int = 3,
) -> RoutePlan | None:
    regions = regions_in_message(user_message)
    picked = pick_regional_spots(spots, regions, limit=limit) if regions else spots[:limit]
    if len(picked) < 2:
        return None
    return plan_route_for_spots(picked)
