"""
강원도 홈 화면 콘텐츠 (추후 한국관광공사 API 연동 예정).

TODO: KTO Tour API / KorService 연동 시 이 모듈의 fetch 함수만 교체.
"""

from typing import Any


def get_weather() -> dict[str, str]:
    """Placeholder — 추후 기상청/KTO API."""
    return {
        "region": "춘천 기준",
        "temp": "12°C",
        "condition": "맑음 · 미세먼지 좋음",
        "tip": "일교차가 커요. 겉옷을 챙기세요.",
    }


def get_festivals() -> list[dict[str, str]]:
    """Placeholder — 추후 KTO 축제 API."""
    return [
        {
            "title": "평창 송어축제",
            "period": "겨울 시즌",
            "place": "평창군",
            "desc": "얼음낚시·지역 먹거리",
        },
        {
            "title": "강릉 커피축제",
            "period": "10월",
            "place": "강릉시",
            "desc": "안목·경포 카페 거리",
        },
        {
            "title": "정선 아리랑제",
            "period": "10월",
            "place": "정선군",
            "desc": "전통 공연·레일바이크",
        },
    ]


def get_highlights() -> list[dict[str, Any]]:
    """홈 화면 사진/명소 카드 — 추후 KTO 이미지 URL."""
    return [
        {
            "title": "설악산 단풍",
            "region": "속초·고성",
            "emoji": "🏔️",
            "gradient": "linear-gradient(135deg,#0D9488,#14B8A6)",
        },
        {
            "title": "남이섬·소나무",
            "region": "춘천",
            "emoji": "🌲",
            "gradient": "linear-gradient(135deg,#0891B2,#22D3EE)",
        },
        {
            "title": "동해 해변 드라이브",
            "region": "동해·삼척",
            "emoji": "🌊",
            "gradient": "linear-gradient(135deg,#0284C7,#38BDF8)",
        },
    ]


def get_region_intro() -> str:
    return (
        "강원도는 산·바다·계곡이 가까워 **당일·반나절 여행**에 잘 맞아요. "
        "AI가 전역 관광지 중에서 취향에 맞는 동선을 골라 드립니다."
    )
