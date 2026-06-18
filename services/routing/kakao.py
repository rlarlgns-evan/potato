"""Kakao Mobility Directions REST API client."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any


KAKAO_DIRECTIONS_URL = "https://apis-navi.kakaomobility.com/v1/directions"


@dataclass(frozen=True)
class LatLng:
    lng: float
    lat: float
    name: str = ""


@dataclass
class RouteLeg:
    from_name: str
    to_name: str
    distance_m: int
    duration_s: int
    summary: str


@dataclass
class RoutePlan:
    spots: list[dict[str, Any]]
    legs: list[RouteLeg] = field(default_factory=list)
    polyline: list[tuple[float, float]] = field(default_factory=list)  # (lat, lng)
    total_distance_m: int = 0
    total_duration_s: int = 0
    provider: str = "kakao"


def _fmt_km(m: int) -> str:
    km = m / 1000
    return f"{km:.1f}km" if km >= 1 else f"{m}m"


def _fmt_min(s: int) -> str:
    minutes = max(1, round(s / 60))
    if minutes < 60:
        return f"{minutes}분"
    h, r = divmod(minutes, 60)
    return f"{h}시간 {r}분" if r else f"{h}시간"


def fetch_kakao_directions(
    points: list[LatLng],
    *,
    rest_key: str | None = None,
) -> dict[str, Any]:
    if len(points) < 2:
        raise ValueError("need at least 2 points")
    if len(points) > 7:
        raise ValueError("kakao supports max 5 waypoints (7 points total)")

    key = (rest_key or os.getenv("KAKAO_REST_KEY") or "").strip()
    if not key:
        raise RuntimeError("KAKAO_REST_KEY not set")

    origin, destination = points[0], points[-1]
    middle = points[1:-1]
    params: dict[str, str] = {
        "origin": f"{origin.lng},{origin.lat}",
        "destination": f"{destination.lng},{destination.lat}",
        "priority": "RECOMMEND",
    }
    if middle:
        params["waypoints"] = "|".join(f"{p.lng},{p.lat}" for p in middle)

    url = f"{KAKAO_DIRECTIONS_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"KakaoAK {key}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"kakao directions HTTP {exc.code}: {body}") from exc


def parse_kakao_route(spots: list[dict[str, Any]], data: dict[str, Any]) -> RoutePlan:
    route = (data.get("routes") or [None])[0]
    if not route:
        raise ValueError("empty kakao route")

    polyline: list[tuple[float, float]] = []
    legs: list[RouteLeg] = []
    names = [str(s.get("name") or "") for s in spots]

    for i, section in enumerate(route.get("sections") or []):
        for road in section.get("roads") or []:
            verts = road.get("vertexes") or []
            for j in range(0, len(verts) - 1, 2):
                polyline.append((verts[j + 1], verts[j]))

        if i < len(names) - 1:
            dist = int(section.get("distance") or 0)
            dur = int(section.get("duration") or 0)
            to_name = names[i + 1]
            legs.append(
                RouteLeg(
                    from_name=names[i],
                    to_name=to_name,
                    distance_m=dist,
                    duration_s=dur,
                    summary=f"{to_name}까지 {_fmt_km(dist)} · 차량 약 {_fmt_min(dur)} (카카오)",
                )
            )

    summary = route.get("summary") or {}
    return RoutePlan(
        spots=spots,
        legs=legs,
        polyline=polyline,
        total_distance_m=int(summary.get("distance") or 0),
        total_duration_s=int(summary.get("duration") or 0),
        provider="kakao",
    )
