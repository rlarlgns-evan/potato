"""Observable curation source labels — No Silent Fallback."""

SOURCE_LABELS: dict[str, str] = {
    "gemini": "✓ Gemini",
    "openai": "✓ OpenAI",
    "local_skip": "◆ 로컬 매칭 (API 절약)",
    "local": "◆ 로컬 AI",
    "local_api_fail": "◆ 로컬 (API 실패)",
}


def source_label(source: str | None) -> str:
    return SOURCE_LABELS.get(source or "", "◆ 로컬 AI")
