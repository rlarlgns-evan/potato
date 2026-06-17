#!/usr/bin/env python3
"""Fetch all 6 KTO APIs in parallel and write data/tour_*.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kto_aggregation_service import KtoAggregationService

DATA = ROOT / "data"

OUTPUT_MAP = {
    "stats": "tour_visitor_stats.json",
    "hub": "tour_hub_spots.json",
    "relate": "tour_relate_spots.json",
    "photos": "tour_region_photos.json",
    "kor": "tour_kor_spots.json",
    "eco": "tour_eco_spots.json",
    "festivals": "tour_kor_festivals.json",
}


def main() -> int:
    svc = KtoAggregationService(DATA)
    loaded = svc.fetch_apis_parallel(days=7, per_region_photos=2)

    for key, fname in OUTPUT_MAP.items():
        payload = loaded.get(key) or {}
        path = DATA / fname
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        status = svc.source_status.get(key)
        flag = "OK" if status and status.ok else "FAIL"
        err = f" ({status.error})" if status and status.error else ""
        print(f"[{flag}] {fname}{err}")

    agg = svc.build_aggregated_export()
    (DATA / "kto_aggregated_spots.json").write_text(
        json.dumps(agg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("Wrote kto_aggregated_spots.json")

    failed = [k for k, st in svc.source_status.items() if not st.ok]
    return 1 if failed and len(failed) == len(OUTPUT_MAP) else 0


if __name__ == "__main__":
    raise SystemExit(main())
