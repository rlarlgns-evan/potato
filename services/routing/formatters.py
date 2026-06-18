"""Format Kakao route plans for Gemini system prompts."""

from __future__ import annotations

from services.routing.kakao import RoutePlan


def _fmt_km(m: int) -> str:
    km = m / 1000
    return f"{km:.1f}km" if km >= 1 else f"{m}m"


def _fmt_min(s: int) -> str:
    minutes = max(1, round(s / 60))
    if minutes < 60:
        return f"{minutes} mins"
    h, r = divmod(minutes, 60)
    return f"{h}h {r}m" if r else f"{h}h"


def routing_context_for_gemini(plan: RoutePlan) -> str:
    lines = [
        "# ROUTING DATA (Kakao Mobility Directions — IMMUTABLE)",
        "Pre-calculated driving times for Gangwon-do roads (NOT straight-line).",
        "Do NOT invent, estimate, or change travel distance/duration/stop order.",
        "",
        f"Total driving: {_fmt_km(plan.total_distance_m)}, {_fmt_min(plan.total_duration_s)}",
        "",
        "Legs:",
    ]
    for i, leg in enumerate(plan.legs, start=1):
        lines.append(
            f'{i}. {leg.from_name} -> {leg.to_name}: '
            f"Driving time {_fmt_min(leg.duration_s)}, Distance {_fmt_km(leg.distance_m)}"
        )
    lines.append("")
    lines.append("Fixed stop order (spot_name MUST match exactly):")
    for i, spot in enumerate(plan.spots, start=1):
        region = spot.get("region") or ""
        lines.append(f"  {i}. {spot['name']}" + (f" ({region})" if region else ""))
    return "\n".join(lines)
