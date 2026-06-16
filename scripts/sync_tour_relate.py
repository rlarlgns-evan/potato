#!/usr/bin/env python3
"""TourAPI 연관관광지 → data/tour_relate_spots.json"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tour_api import TourApiError, fetch_gangwon_relate_spots

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

OUT = ROOT / "data" / "tour_relate_spots.json"


def empty_payload() -> dict:
    return {
        "source": "TourAPI TarRlteTarService1 areaBasedList1",
        "updated_at": None,
        "baseYm": None,
        "regions": {},
        "by_anchor": {},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ym", help="기준연월 YYYYMM (기본: 전월)")
    parser.add_argument("--top", type=int, default=5, help="기준 관광지당 연관 상위 N개")
    args = parser.parse_args()

    try:
        data = fetch_gangwon_relate_spots(base_ym=args.base_ym, top_n_per_anchor=args.top)
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        n = len(data.get("regions", {}))
        print(f"Wrote {OUT} ({n} regions)")
        if n == 0:
            print(
                "Relate sync warning: no data — 공공데이터포털에서 "
                "「관광지별 연관관광지 정보서비스_GW」 활용신청·403 여부를 확인하세요.",
                file=sys.stderr,
            )
        return 0
    except TourApiError as exc:
        print(f"Relate sync skipped: {exc}", file=sys.stderr)
        if not OUT.exists():
            OUT.write_text(json.dumps(empty_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
