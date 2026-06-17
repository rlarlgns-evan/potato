"""
KTO 6-API aggregation layer — AI-ready normalized spots.

Sources (batch JSON or live fetch):
  1. 관광빅데이터 (tour_visitor_stats.json)
  2. 중심관광지 (tour_hub_spots.json)
  3. 연관관광지 (tour_relate_spots.json)
  4. 관광사진 (tour_region_photos.json)
  5. 생태관광 (tour_eco_spots.json)
  6. 국문 관광정보 (tour_kor_spots.json, tour_kor_festivals.json)
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

from tour_api import GANGWON_REGIONS, TourApiError

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

SOURCE_FILES: dict[str, str] = {
    "stats": "tour_visitor_stats.json",
    "hub": "tour_hub_spots.json",
    "relate": "tour_relate_spots.json",
    "photos": "tour_region_photos.json",
    "kor": "tour_kor_spots.json",
    "eco": "tour_eco_spots.json",
    "festivals": "tour_kor_festivals.json",
}


@dataclass
class SourceStatus:
    key: str
    ok: bool
    error: str | None = None
    path: str | None = None


@dataclass
class AggregatedSpot:
    """Essential fields only — no raw API payloads."""

    name: str
    region: str
    theme: str
    description: str
    image_url: str
    visitor_count: int | str
    related: list[str] = field(default_factory=list)
    rank: int = 999
    sources: list[str] = field(default_factory=list)
    lat: float | None = None
    lng: float | None = None
    category_label: str = ""

    def to_catalog_entry(self) -> dict[str, Any]:
        """Backward-compatible shape for gangwon_agent_prompt / app.js."""
        theme_key = "nature" if "자연" in self.theme or "생태" in self.theme else (
            "experience" if "레저" in self.theme or "체험" in self.theme else "culture"
        )
        return {
            "name": self.name,
            "region": self.region,
            "theme": theme_key,
            "rank": self.rank,
            "source": ", ".join(self.sources) if self.sources else "KTO",
            "lat": self.lat,
            "lng": self.lng,
            "categoryLabel": self.category_label or self.theme,
            "description": self.description,
            "imageUrl": self.image_url,
            "related": list(self.related),
            "visitorCount": self.visitor_count,
        }

    def to_ai_xml_line(self, *, include_description: bool = False) -> str:
        related = ", ".join(self.related[:3]) if self.related else ""
        attrs = [
            f'name="{_xml_escape(self.name)}"',
            f'region="{_xml_escape(self.region.rstrip("시군"))}"',
            f'theme="{_xml_escape(self.theme)}"',
            f'visitors="{self.visitor_count}"',
        ]
        if self.image_url:
            attrs.append(f'image="{_xml_escape(self.image_url)}"')
        if related:
            attrs.append(f'related="{_xml_escape(related)}"')
        if include_description and self.description:
            body = _xml_escape(self.description[:120])
            return f"  <spot {' '.join(attrs)}>{body}</spot>"
        return f"  <spot {' '.join(attrs)}/>"


def _xml_escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def norm_spot_key(name: str) -> str:
    return re.sub(r"[\s·\-]+", "", (name or "").strip())


def title_matches_spot(title: str, spot_name: str) -> bool:
    t, n = norm_spot_key(title), norm_spot_key(spot_name)
    if not t or not n:
        return False
    if t in n or n in t:
        return True
    parts = re.split(r"[\s·\-]+", spot_name)
    return any(len(p) >= 2 and p in title for p in parts)


def _theme_from_category(category: str) -> str:
    cat = category or ""
    if any(x in cat for x in ("자연", "생태", "산", "숲", "경관")):
        return "자연/풍경"
    if any(x in cat for x in ("레저", "스포츠", "체험")):
        return "레저/체험"
    if any(x in cat for x in ("문화", "예술", "역사")):
        return "문화/예술"
    return cat.replace("관광", "").strip() or "관광"


def _estimate_spot_visitors(region_stats: dict[str, Any] | None, rank: int) -> int | str:
    if not region_stats:
        return "—"
    base = region_stats.get("avg_daily") or region_stats.get("total") or 0
    try:
        base = float(base)
    except (TypeError, ValueError):
        return "—"
    if base <= 0:
        return "—"
    weight = (6 - min(rank, 5)) / 15 if rank <= 5 else 1 / (rank + 5)
    return max(100, int(round(base * weight)))


class KtoAggregationService:
    """Load 6 KTO sources in parallel, merge by region/name, format for LLM."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or DATA_DIR
        self._sources: dict[str, Any] | None = None
        self._status: dict[str, SourceStatus] = {}

    @property
    def source_status(self) -> dict[str, SourceStatus]:
        if self._sources is None:
            self.load_sources_parallel()
        return dict(self._status)

    def load_sources_parallel(self, *, force: bool = False) -> dict[str, Any]:
        if self._sources is not None and not force:
            return self._sources

        def _read(key: str) -> tuple[str, Any, SourceStatus]:
            fname = SOURCE_FILES[key]
            path = self.data_dir / fname
            try:
                if not path.exists():
                    return key, {}, SourceStatus(key, False, "file missing", str(path))
                data = json.loads(path.read_text(encoding="utf-8"))
                return key, data, SourceStatus(key, True, path=str(path))
            except (json.JSONDecodeError, OSError) as exc:
                return key, {}, SourceStatus(key, False, str(exc), str(path))

        loaded: dict[str, Any] = {}
        statuses: dict[str, SourceStatus] = {}
        with ThreadPoolExecutor(max_workers=len(SOURCE_FILES)) as pool:
            futures = [pool.submit(_read, key) for key in SOURCE_FILES]
            for fut in as_completed(futures):
                key, data, status = fut.result()
                loaded[key] = data
                statuses[key] = status

        self._sources = loaded
        self._status = statuses
        return loaded

    def fetch_apis_parallel(
        self,
        *,
        days: int = 7,
        per_region_photos: int = 2,
        service_key: str | None = None,
        throttle_sec: float = 0.0,
    ) -> dict[str, Any]:
        """Live fetch from 6 TourAPI endpoints concurrently (sync/refresh)."""
        from tour_api import (
            fetch_gangwon_eco_spots,
            fetch_gangwon_hub_spots,
            fetch_gangwon_kor_festivals,
            fetch_gangwon_kor_spots,
            fetch_gangwon_region_photos,
            fetch_gangwon_relate_spots,
            fetch_gangwon_visitor_stats,
        )

        jobs: dict[str, Callable[[], dict[str, Any]]] = {
            "stats": lambda: fetch_gangwon_visitor_stats(days=days, service_key=service_key),
            "hub": lambda: fetch_gangwon_hub_spots(service_key=service_key, throttle_sec=throttle_sec),
            "relate": lambda: fetch_gangwon_relate_spots(service_key=service_key, throttle_sec=throttle_sec),
            "photos": lambda: fetch_gangwon_region_photos(
                per_region=per_region_photos, service_key=service_key, throttle_sec=throttle_sec
            ),
            "kor": lambda: fetch_gangwon_kor_spots(service_key=service_key, throttle_sec=throttle_sec),
            "eco": lambda: fetch_gangwon_eco_spots(service_key=service_key, throttle_sec=throttle_sec),
            "festivals": lambda: fetch_gangwon_kor_festivals(service_key=service_key, throttle_sec=throttle_sec),
        }

        loaded: dict[str, Any] = {}
        statuses: dict[str, SourceStatus] = {}

        def _run(key: str, fn: Callable[[], dict[str, Any]]) -> tuple[str, Any, SourceStatus]:
            try:
                return key, fn(), SourceStatus(key, True)
            except (TourApiError, OSError, TimeoutError) as exc:
                return key, {}, SourceStatus(key, False, str(exc))

        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(_run, k, fn): k for k, fn in jobs.items()}
            for fut in as_completed(futures):
                key, data, status = fut.result()
                loaded[key] = data
                statuses[key] = status

        self._sources = loaded
        self._status = statuses
        return loaded

    def _region_stats(self, region: str) -> dict[str, Any] | None:
        src = self.load_sources_parallel()
        return (src.get("stats") or {}).get("regions", {}).get(region)

    def _photo_for_spot(self, region: str, spot_name: str) -> str:
        src = self.load_sources_parallel()
        kor = (src.get("kor") or {}).get("regions", {}).get(region, [])
        for item in kor:
            if title_matches_spot(str(item.get("title") or ""), spot_name) and item.get("image"):
                return str(item["image"])
        eco = (src.get("eco") or {}).get("regions", {}).get(region, [])
        for item in eco:
            if title_matches_spot(str(item.get("title") or ""), spot_name) and item.get("image"):
                return str(item["image"])
        photos = (src.get("photos") or {}).get("regions", {}).get(region, [])
        for item in photos:
            title = str(item.get("title") or "")
            kw = str(item.get("keyword") or "")
            if title_matches_spot(title, spot_name) or title_matches_spot(kw, spot_name):
                if item.get("image"):
                    return str(item["image"])
        if photos and photos[0].get("image"):
            return str(photos[0]["image"])
        return ""

    def _related_for_anchor(self, region: str, anchor_name: str) -> list[str]:
        src = self.load_sources_parallel()
        by_anchor = (src.get("relate") or {}).get("by_anchor", {}).get(region, {})
        rows = by_anchor.get(anchor_name) or []
        if not rows:
            # fuzzy anchor match
            key = norm_spot_key(anchor_name)
            for anchor, items in by_anchor.items():
                if norm_spot_key(anchor) == key or key in norm_spot_key(anchor):
                    rows = items
                    break
        return [str(r.get("name") or "") for r in rows if r.get("name")][:5]

    def aggregate_region(self, region: str) -> list[AggregatedSpot]:
        """Merge hub + kor + eco; attach stats, photos, related."""
        src = self.load_sources_parallel()
        region_stats = self._region_stats(region)
        buckets: dict[str, AggregatedSpot] = {}

        def upsert(
            name: str,
            *,
            rank: int,
            theme: str,
            source: str,
            description: str = "",
            image_url: str = "",
            lat: float | None = None,
            lng: float | None = None,
            category_label: str = "",
        ) -> AggregatedSpot:
            key = norm_spot_key(name)
            if not name or not key:
                raise ValueError("empty spot name")
            spot = buckets.get(key)
            if spot is None:
                spot = AggregatedSpot(
                    name=name,
                    region=region,
                    theme=theme,
                    description=description,
                    image_url=image_url,
                    visitor_count=_estimate_spot_visitors(region_stats, rank),
                    rank=rank,
                    sources=[source],
                    lat=lat,
                    lng=lng,
                    category_label=category_label,
                )
                buckets[key] = spot
            else:
                if rank < spot.rank:
                    spot.rank = rank
                if source not in spot.sources:
                    spot.sources.append(source)
                if description and not spot.description:
                    spot.description = description
                if image_url and not spot.image_url:
                    spot.image_url = image_url
                if lat is not None and spot.lat is None:
                    spot.lat = lat
                if lng is not None and spot.lng is None:
                    spot.lng = lng
                if category_label and not spot.category_label:
                    spot.category_label = category_label
                spot.visitor_count = _estimate_spot_visitors(region_stats, spot.rank)
            return spot

        for h in (src.get("hub") or {}).get("regions", {}).get(region, []):
            name = str(h.get("name") or "")
            cat = str(h.get("category") or h.get("category_m") or "")
            rank = int(h.get("rank") or 999)
            upsert(
                name,
                rank=rank,
                theme=_theme_from_category(cat),
                source="중심관광지",
                lat=h.get("lat"),
                lng=h.get("lng"),
                category_label=cat,
            )

        for i, k in enumerate((src.get("kor") or {}).get("regions", {}).get(region, [])):
            title = str(k.get("title") or "")
            addr = str(k.get("addr") or "").strip()
            image = str(k.get("image") or "")
            lat = lng = None
            try:
                if k.get("mapY") not in (None, ""):
                    lat = float(k["mapY"])
                if k.get("mapX") not in (None, ""):
                    lng = float(k["mapX"])
            except (TypeError, ValueError):
                pass
            upsert(
                title,
                rank=100 + i,
                theme="문화/예술",
                source="공식관광지",
                description=addr,
                image_url=image,
                lat=lat,
                lng=lng,
            )

        for i, e in enumerate((src.get("eco") or {}).get("regions", {}).get(region, [])):
            title = str(e.get("title") or "")
            summary = str(e.get("summary") or "").strip()
            image = str(e.get("image") or "")
            upsert(
                title,
                rank=200 + i,
                theme="자연/풍경",
                source="생태관광",
                description=summary,
                image_url=image,
            )

        for spot in buckets.values():
            if not spot.image_url:
                spot.image_url = self._photo_for_spot(region, spot.name)
            spot.related = self._related_for_anchor(region, spot.name)
            if not spot.description and spot.related:
                spot.description = f"연관 관광지: {', '.join(spot.related[:3])}"

        out = sorted(buckets.values(), key=lambda s: (s.rank, s.name))
        return out

    def catalog_entries_for_region(self, region: str) -> list[dict[str, Any]]:
        return [s.to_catalog_entry() for s in self.aggregate_region(region)]

    def build_aggregated_export(self) -> dict[str, Any]:
        """Pre-compute all regions for docs/data.js (TOUR_AGGREGATED_SPOTS)."""
        self.load_sources_parallel()
        regions: dict[str, list[dict[str, Any]]] = {}
        for region in GANGWON_REGIONS:
            spots = self.aggregate_region(region)
            if spots:
                regions[region] = [s.to_catalog_entry() for s in spots]
        return {
            "updated_at": date.today().isoformat(),
            "source_status": {k: {"ok": v.ok, "error": v.error} for k, v in self.source_status.items()},
            "regions": regions,
        }

    def format_ai_xml(
        self,
        regions: list[str],
        *,
        max_spots: int = 12,
        compact: bool = True,
    ) -> str:
        """Token-efficient <spot/> XML for Gemini system prompt."""
        lines = ["<kto_data>"]
        count = 0
        for region in regions:
            if count >= max_spots:
                break
            for spot in self.aggregate_region(region):
                if count >= max_spots:
                    break
                lines.append(spot.to_ai_xml_line(include_description=not compact))
                count += 1
        lines.append("</kto_data>")
        return "\n".join(lines) if count else "<kto_data>\n</kto_data>"

    def format_ai_table_xml(
        self,
        regions: list[str],
        *,
        max_rows: int = 12,
        theme_fn: Callable[[dict[str, Any]], str] | None = None,
    ) -> str:
        """Legacy markdown table inside <kto_data> (backward compatible)."""
        rows: list[tuple[str, str, str, str | int]] = []
        for region in regions:
            for entry in self.catalog_entries_for_region(region):
                if len(rows) >= max_rows:
                    break
                theme = theme_fn(entry) if theme_fn else str(entry.get("categoryLabel") or entry.get("theme"))
                rows.append(
                    (
                        region.rstrip("시군"),
                        entry["name"],
                        theme,
                        entry.get("visitorCount", "—"),
                    )
                )
            if len(rows) >= max_rows:
                break
        if not rows:
            return "<kto_data>\n</kto_data>"
        header = "| 지역 | 관광지명 | 생태/테마 | 방문자수(빅데이터) |"
        sep = "|---|---|---|---|"
        body = "\n".join(f"| {r} | {n} | {t} | {v} |" for r, n, t, v in rows)
        return f"<kto_data>\n{header}\n{sep}\n{body}\n</kto_data>"


_default_service: KtoAggregationService | None = None


def get_kto_aggregation_service() -> KtoAggregationService:
    global _default_service
    if _default_service is None:
        _default_service = KtoAggregationService()
    return _default_service
