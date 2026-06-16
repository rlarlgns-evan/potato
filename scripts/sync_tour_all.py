#!/usr/bin/env python3
"""TourAPI 전체 동기화 (방문자·중심관광지·관광사진) + docs/data.js 생성."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(script: str, *args: str) -> int:
    cmd = [sys.executable, str(ROOT / "scripts" / script), *args]
    print(">", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    codes = 0
    codes |= run("sync_tour_ldong.py")
    codes |= run("sync_tour_stats.py", "--days", "7")
    codes |= run("sync_tour_hub.py")
    codes |= run("sync_tour_photos.py", "--per-region", "2")
    codes |= run("sync_tour_kor.py")
    codes |= run("sync_tour_eco.py")
    codes |= run("sync_content.py", "generate")
    return 0 if codes == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
