#!/usr/bin/env python3
"""TourAPI 관광빅데이터 → data/tour_visitor_stats.json 동기화.

Usage:
  set TOUR_API_SERVICE_KEY=...   # Windows
  export TOUR_API_SERVICE_KEY=... # macOS/Linux
  python scripts/sync_tour_stats.py
  python scripts/sync_tour_stats.py --days 7

이후 docs 반영:
  python scripts/sync_content.py generate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tour_api import TourApiError, fetch_gangwon_visitor_stats, fetch_metco_gangwon_summary

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

OUT = ROOT / "data" / "tour_visitor_stats.json"


def empty_payload() -> dict:
    return {
        "source": "TourAPI DataLab",
        "updated_at": None,
        "period": None,
        "province": None,
        "regions": {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Gangwon visitor stats from TourAPI DataLab")
    parser.add_argument("--days", type=int, default=7, help="집계 일수 (기본 7)")
    args = parser.parse_args()

    try:
        stats = fetch_gangwon_visitor_stats(days=args.days)
        province = fetch_metco_gangwon_summary(days=args.days)
        if province:
            stats["province"] = province
        OUT.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {OUT} ({len(stats.get('regions', {}))} regions)")
        return 0
    except TourApiError as exc:
        print(f"TourAPI sync skipped: {exc}", file=sys.stderr)
        if not OUT.exists():
            OUT.write_text(json.dumps(empty_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Created empty placeholder at {OUT}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
