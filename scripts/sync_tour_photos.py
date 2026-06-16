#!/usr/bin/env python3
"""TourAPI 관광사진 → data/tour_region_photos.json"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tour_api import TourApiError, fetch_gangwon_region_photos

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

OUT = ROOT / "data" / "tour_region_photos.json"


def empty_payload() -> dict:
    return {
        "source": "TourAPI PhotoGalleryService1 gallerySearchList1",
        "updated_at": None,
        "regions": {},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-region", type=int, default=2, help="지역당 사진 수")
    args = parser.parse_args()

    try:
        data = fetch_gangwon_region_photos(per_region=args.per_region)
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {OUT} ({len(data.get('regions', {}))} regions)")
        return 0
    except TourApiError as exc:
        print(f"Photo sync skipped: {exc}", file=sys.stderr)
        if not OUT.exists():
            OUT.write_text(json.dumps(empty_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
