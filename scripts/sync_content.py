#!/usr/bin/env python3
"""Sync canonical data/*.json → docs/data.js (+ optional DB seed).

SSoT: data/spots.json, data/catalog.json
Generated: docs/data.js (do not hand-edit the JSON blocks)

Usage:
  python scripts/sync_content.py bootstrap   # one-time: extract from docs/data.js
  python scripts/sync_content.py generate    # write docs/data.js
  python scripts/sync_content.py --check     # CI: fail if data.js is stale
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOCS_DATA = ROOT / "docs" / "data.js"
MARKER = "// === CANONICAL DATA (auto-generated from data/*.json) ==="


def _js_array_block(name: str, data: object) -> str:
    return f"const {name} = {json.dumps(data, ensure_ascii=False, indent=2)};"


def bootstrap_from_docs() -> None:
    """Extract JSON blocks from legacy docs/data.js into data/*.json."""
    script = ROOT / "scripts" / "_extract_data.mjs"
    subprocess.run(
        ["node", str(script)],
        check=True,
        cwd=str(ROOT),
    )
    print(f"Bootstrapped {DATA_DIR / 'spots.json'} and catalog.json")


def generate_data_js() -> str:
    spots = json.loads((DATA_DIR / "spots.json").read_text(encoding="utf-8"))
    catalog = json.loads((DATA_DIR / "catalog.json").read_text(encoding="utf-8"))

    highlights = [
        {**h, "bg": h.get("bg") or h.get("thumb_bg")}
        for h in catalog["highlights"]
    ]
    weather_icons = {
        k: {**v, "bg": v.get("bg") or v.get("thumb_bg")}
        for k, v in catalog["weather_icons"].items()
    }

    blocks = [
        _js_array_block("SPOTS", spots),
        _js_array_block("GANGWON_CITIES", catalog["cities"]),
        _js_array_block("FESTIVALS", catalog["festivals"]),
        _js_array_block("HIGHLIGHTS", highlights),
        _js_array_block("THEME_META", catalog["theme_meta"]),
        _js_array_block("SPOT_OVERRIDES", catalog["spot_overrides"]),
        _js_array_block("FESTIVAL_ICONS", catalog["festival_icons"]),
        _js_array_block("WEATHER_ICONS", weather_icons),
        _js_array_block("THEME_BADGE", catalog["theme_badge"]),
        _js_array_block("THEME_IMAGE", catalog["theme_image"]),
        f'const DEFAULT_IMAGE = {json.dumps(catalog["default_image"], ensure_ascii=False)};',
        f'const REGION_INTRO = {json.dumps(catalog["region_intro_html"], ensure_ascii=False)};',
        _js_array_block("SUGGESTIONS", catalog["suggestions"]),
        f'const GEMINI_MODEL = {json.dumps(catalog["gemini_model"], ensure_ascii=False)};',
        _js_array_block("TRANSIT_ORIGINS", catalog.get("transit_origins") or {}),
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
// Kakao·Gemini 키는 저장소에 두지 않습니다.
// - 로컬: docs/config.example.js → config.js
// - 배포: GitHub Actions Secret (KAKAO_JS_KEY, GOOGLE_API_KEY)
"""
    return header + "\n\n".join(blocks) + runtime + footer


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] == "generate":
        content = generate_data_js()
        DOCS_DATA.write_text(content, encoding="utf-8")
        print(f"Wrote {DOCS_DATA}")
        return 0
    if args[0] == "bootstrap":
        bootstrap_from_docs()
        generate_data_js()
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
    print("Usage: bootstrap | generate | --check", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
