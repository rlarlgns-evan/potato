#!/usr/bin/env python3
"""Kor 법정동·Eco 시군구 코드 → data/gangwon_sigungu_codes.json 보강."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tour_api import TourApiError, enrich_gangwon_sigungu_codes

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def main() -> int:
    try:
        data = enrich_gangwon_sigungu_codes()
        mapped_ldong = sum(
            1 for r, m in data.get("regions", {}).items() if m.get("lDongSignguCd")
        )
        mapped_eco = sum(
            1 for r, m in data.get("regions", {}).items() if m.get("ecoSigunguCode") is not None
        )
        print(
            f"Enriched gangwon_sigungu_codes.json "
            f"(ldong={mapped_ldong}, eco={mapped_eco}, lDongRegnCd={data.get('lDongRegnCd')})"
        )
        return 0
    except TourApiError as exc:
        print(f"Ldong/eco code sync skipped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
