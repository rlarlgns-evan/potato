"""Canonical content loader — SSoT is data/*.json only."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"


def _read_json(name: str) -> Any:
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing canonical data file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_spots() -> list[dict[str, Any]]:
    return _read_json("spots.json")


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    return _read_json("catalog.json")


def load_festivals() -> list[dict[str, str]]:
    return load_catalog()["festivals"]


def load_cities() -> list[dict[str, Any]]:
    return load_catalog()["cities"]


def load_highlights() -> list[dict[str, Any]]:
    return load_catalog()["highlights"]


def load_suggestions() -> list[dict[str, str]]:
    return load_catalog()["suggestions"]


def load_theme_meta() -> dict[str, Any]:
    return load_catalog()["theme_meta"]


def load_spot_overrides() -> dict[str, Any]:
    return load_catalog()["spot_overrides"]


def load_region_intro_html() -> str:
    return load_catalog()["region_intro_html"]


def load_region_intro_md() -> str:
    return load_catalog()["region_intro_md"]
