#!/usr/bin/env python3
"""Sync canonical data/*.json → docs/data.js.

SSoT: data/spots.json, data/catalog.json, data/prompts.json
Generated: docs/data.js (do not hand-edit the JSON blocks)

Usage:
  python scripts/sync_content.py generate    # write docs/data.js
  python scripts/sync_content.py --check     # CI: fail if data.js is stale
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOCS_DATA = ROOT / "docs" / "data.js"
MARKER = "// === CANONICAL DATA (auto-generated from data/*.json) ==="


def _norm_name(s: str) -> str:
    return re.sub(r"[\s·\-]+", "", (s or "").strip())


def _title_matches_spot(title: str, spot_name: str) -> bool:
    t, n = _norm_name(title), _norm_name(spot_name)
    if not t or not n:
        return False
    if t in n or n in t:
        return True
    parts = re.split(r"[\s·\-]+", spot_name)
    return any(len(p) >= 2 and p in title for p in parts)


def build_spot_tour_images(
    spots: list[dict],
    tour_aggregated: dict,
    tour_photos: dict,
) -> dict[str, str]:
    agg_r = tour_aggregated.get("regions") or {}
    photo_r = tour_photos.get("regions") or {}
    out: dict[str, str] = {}
    for spot in spots:
        name = str(spot.get("name") or "")
        region = str(spot.get("region") or "")
        if not name or not region:
            continue
        url: str | None = None
        for entry in agg_r.get(region, []):
            entry_name = str(entry.get("name") or "")
            entry_url = str(entry.get("imageUrl") or "")
            if entry_url and _title_matches_spot(entry_name, name):
                url = entry_url
                break
        if not url:
            reg_photos = photo_r.get(region) or []
            if reg_photos and reg_photos[0].get("image"):
                url = str(reg_photos[0]["image"])
        if url:
            out[name] = url
    return out


def build_region_tour_photos(tour_photos: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for region, items in (tour_photos.get("regions") or {}).items():
        if items and items[0].get("image"):
            out[region] = str(items[0]["image"])
    return out


def _js_array_block(name: str, data: object) -> str:
    return f"const {name} = {json.dumps(data, ensure_ascii=False, indent=2)};"


def generate_data_js() -> str:
    spots = json.loads((DATA_DIR / "spots.json").read_text(encoding="utf-8"))
    catalog = json.loads((DATA_DIR / "catalog.json").read_text(encoding="utf-8"))
    tour_stats_path = DATA_DIR / "tour_visitor_stats.json"
    tour_stats = (
        json.loads(tour_stats_path.read_text(encoding="utf-8"))
        if tour_stats_path.exists()
        else {"regions": {}, "province": None}
    )
    tour_relate_path = DATA_DIR / "tour_relate_spots.json"
    tour_relate = (
        json.loads(tour_relate_path.read_text(encoding="utf-8"))
        if tour_relate_path.exists()
        else {"regions": {}, "by_anchor": {}}
    )
    tour_photos_path = DATA_DIR / "tour_region_photos.json"
    tour_photos = (
        json.loads(tour_photos_path.read_text(encoding="utf-8"))
        if tour_photos_path.exists()
        else {"regions": {}}
    )
    tour_kor_fest_path = DATA_DIR / "tour_kor_festivals.json"
    tour_kor_fest = (
        json.loads(tour_kor_fest_path.read_text(encoding="utf-8"))
        if tour_kor_fest_path.exists()
        else {"items": [], "regions": {}}
    )
    weather_icons = {
        k: {**v, "bg": v.get("bg") or v.get("thumb_bg")}
        for k, v in catalog["weather_icons"].items()
    }

    # 6-source AI aggregation (hub+kor+eco+relate+photos+stats)
    sys.path.insert(0, str(ROOT))
    from kto_aggregation_service import KtoAggregationService

    tour_aggregated = KtoAggregationService(DATA_DIR).build_aggregated_export()
    agg_path = DATA_DIR / "kto_aggregated_spots.json"
    agg_path.write_text(json.dumps(tour_aggregated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    spot_tour_images = build_spot_tour_images(spots, tour_aggregated, tour_photos)
    region_tour_photos = build_region_tour_photos(tour_photos)

    prompts_path = DATA_DIR / "prompts.json"
    tour_prompts = (
        json.loads(prompts_path.read_text(encoding="utf-8"))
        if prompts_path.exists()
        else {}
    )

    blocks = [
        _js_array_block("SPOTS", spots),
        _js_array_block("GANGWON_CITIES", catalog["cities"]),
        _js_array_block("THEME_META", catalog["theme_meta"]),
        _js_array_block("SPOT_OVERRIDES", catalog["spot_overrides"]),
        _js_array_block("FESTIVAL_ICONS", catalog["festival_icons"]),
        _js_array_block("WEATHER_ICONS", weather_icons),
        _js_array_block("THEME_BADGE", catalog["theme_badge"]),
        f'const GEMINI_MODEL = {json.dumps(catalog["gemini_model"], ensure_ascii=False)};',
        _js_array_block("TRANSIT_ORIGINS", catalog.get("transit_origins") or {}),
        f"const TOUR_VISITOR_STATS = {json.dumps(tour_stats, ensure_ascii=False, indent=2)};",
        f"const TOUR_RELATE_SPOTS = {json.dumps(tour_relate, ensure_ascii=False, indent=2)};",
        f"const TOUR_KOR_FESTIVALS = {json.dumps(tour_kor_fest, ensure_ascii=False, indent=2)};",
        f"const TOUR_AGGREGATED_SPOTS = {json.dumps(tour_aggregated, ensure_ascii=False, indent=2)};",
        f"const TOUR_PROMPTS = {json.dumps(tour_prompts, ensure_ascii=False, indent=2)};",
        f"const SPOT_TOUR_IMAGES = {json.dumps(spot_tour_images, ensure_ascii=False, indent=2)};",
        f"const REGION_TOUR_PHOTOS = {json.dumps(region_tour_photos, ensure_ascii=False, indent=2)};",
    ]

    runtime = """
function enrichSpot(raw) {
  const theme = THEME_META[raw.theme] || {};
  const extra = SPOT_OVERRIDES[raw.name] || {};
  return {
    ...raw,
    lat: extra.map_lat ?? raw.lat,
    lng: extra.map_lng ?? raw.lng,
    stay_min: extra.stay_min ?? theme.stay_min ?? 60,
    fee: extra.fee ?? theme.fee ?? "현장 확인",
    hours: extra.hours ?? theme.hours ?? "연중",
    parking: extra.parking ?? theme.parking ?? "인근 주차 가능",
    best_time: extra.best_time ?? theme.best_time ?? "주말·휴일",
    tip: extra.tip ?? theme.tip ?? raw.description,
    contentId: extra.contentId ?? raw.contentId ?? null,
    tourImage: SPOT_TOUR_IMAGES[raw.name] ?? null,
    tags: extra.tags ?? [raw.theme, raw.region.replace(/[시군]$/, "")],
  };
}

const ENRICHED_SPOTS = SPOTS.map(enrichSpot);
"""

    header = f"""// VoyageAI · 강원 — canonical data lives in data/*.json
// {MARKER}
// Regenerate: python scripts/sync_content.py generate
"use strict";

"""
    footer = """
// API 키는 GitHub Actions Secret → docs/config.js (저장소·로컬 파일 없음)
"""
    return header + "\n\n".join(blocks) + runtime + footer


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] == "generate":
        content = generate_data_js()
        DOCS_DATA.write_text(content, encoding="utf-8")
        print(f"Wrote {DOCS_DATA}")
        return 0
    if args[0] == "--check":
        if not DOCS_DATA.exists():
            print("docs/data.js missing — run sync_content.py generate", file=sys.stderr)
            return 1
        current = DOCS_DATA.read_text(encoding="utf-8")
        expected = generate_data_js()
        if current != expected:
            print("docs/data.js is stale — run: python scripts/sync_content.py generate", file=sys.stderr)
            return 1
        print("docs/data.js is up to date")
        return 0
    print("Usage: generate | --check", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
