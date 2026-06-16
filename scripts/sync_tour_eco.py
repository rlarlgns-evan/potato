#!/usr/bin/env python3
"""TourAPI 생태관광 → data/tour_eco_spots.json"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tour_api import TourApiError, fetch_gangwon_eco_spots

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

OUT = ROOT / "data" / "tour_eco_spots.json"


def empty_payload() -> dict:
    return {
        "source": "TourAPI GreenTourService1 areaBasedList1",
        "updated_at": None,
        "ecoAreaCode": 32,
        "regions": {},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=5, help="시군구당 상위 N개")
    args = parser.parse_args()

    try:
        data = fetch_gangwon_eco_spots(top_n=args.top)
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {OUT} ({len(data.get('regions', {}))} regions)")
        return 0
    except TourApiError as exc:
        print(f"Eco sync skipped: {exc}", file=sys.stderr)
        if not OUT.exists():
            OUT.write_text(json.dumps(empty_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
