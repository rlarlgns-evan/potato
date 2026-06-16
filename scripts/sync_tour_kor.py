#!/usr/bin/env python3
"""TourAPI 국문 관광지·축제 → data/tour_kor_spots.json, tour_kor_festivals.json"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tour_api import TourApiError, fetch_gangwon_kor_festivals, fetch_gangwon_kor_spots

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

SPOTS_OUT = ROOT / "data" / "tour_kor_spots.json"
FEST_OUT = ROOT / "data" / "tour_kor_festivals.json"


def empty_spots() -> dict:
    return {
        "source": "TourAPI KorService2 areaBasedList2",
        "updated_at": None,
        "lDongRegnCd": None,
        "regions": {},
    }


def empty_festivals() -> dict:
    return {
        "source": "TourAPI KorService2 searchFestival2",
        "updated_at": None,
        "year": None,
        "lDongRegnCd": None,
        "regions": {},
        "items": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=5, help="시군구당 관광지 상위 N개")
    parser.add_argument("--year", type=int, help="축제 조회 연도 (기본: 올해)")
    parser.add_argument("--spots-only", action="store_true")
    parser.add_argument("--festivals-only", action="store_true")
    args = parser.parse_args()

    code = 0
    do_spots = not args.festivals_only
    do_fest = not args.spots_only

    if do_spots:
        try:
            spots = fetch_gangwon_kor_spots(top_n=args.top)
            SPOTS_OUT.write_text(
                json.dumps(spots, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Wrote {SPOTS_OUT} ({len(spots.get('regions', {}))} regions)")
        except TourApiError as exc:
            print(f"Kor spots sync skipped: {exc}", file=sys.stderr)
            if not SPOTS_OUT.exists():
                SPOTS_OUT.write_text(
                    json.dumps(empty_spots(), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            code = 1

    if do_fest:
        try:
            festivals = fetch_gangwon_kor_festivals(year=args.year)
            FEST_OUT.write_text(
                json.dumps(festivals, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Wrote {FEST_OUT} ({len(festivals.get('items', []))} festivals)")
        except TourApiError as exc:
            print(f"Kor festivals sync skipped: {exc}", file=sys.stderr)
            if not FEST_OUT.exists():
                FEST_OUT.write_text(
                    json.dumps(empty_festivals(), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            code = 1

    return code


if __name__ == "__main__":
    raise SystemExit(main())
