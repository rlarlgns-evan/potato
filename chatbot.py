import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _build_system_prompt(spots: list[dict[str, Any]]) -> str:
    spot_lines = "\n".join(
        [
            f"- {s['name']} ({s['region']}, {s['theme']}): {s['description']}"
            for s in spots[:20]
        ]
    )
    return f"""
당신은 강원도 인구 감소 지역 여행 큐레이터입니다.
사용자 취향에 맞춰 과도하게 유명하지 않은 장소를 추천합니다.
답변은 반드시 한국어로, 짧고 실용적으로 작성하세요.
추천 시 이유 2가지와 이동 동선 팁 1가지를 포함하세요.

현재 앱 DB 후보지:
{spot_lines if spot_lines else "- 현재 필터 조건에 맞는 후보지가 없습니다."}
""".strip()


def _fallback_reply(user_message: str, spots: list[dict[str, Any]]) -> str:
    if not spots:
        return "현재 조건에 맞는 장소가 없어요. 지역/테마 필터를 조금 넓혀 다시 시도해 주세요."

    keywords = user_message.replace(",", " ").split()
    ranked = []
    for spot in spots:
        score = 0
        text = f"{spot['name']} {spot['region']} {spot['theme']} {spot['description']}"
        for kw in keywords:
            if kw and kw in text:
                score += 1
        ranked.append((score, spot))

    ranked.sort(key=lambda x: (-x[0], x[1]["region"]))
    picks = [spot for _, spot in ranked[:3]]

    lines = ["AI 키가 없어 로컬 추천 로직으로 안내드려요.", "", "추천 장소:"]
    for idx, spot in enumerate(picks, start=1):
        lines.append(f"{idx}. {spot['name']} ({spot['region']}) - {spot['description']}")
    lines.append("")
    lines.append("동선 팁: 같은 군/시 기준으로 묶어 방문하면 이동 시간이 줄어듭니다.")
    return "\n".join(lines)


def generate_reply(
    user_message: str,
    spots: list[dict[str, Any]],
    chat_history: list[dict[str, str]] | None = None,
) -> str:
    provider = os.getenv("AI_PROVIDER", "openai").lower()
    system_prompt = _build_system_prompt(spots)
    history = chat_history or []

    if provider == "google":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return _fallback_reply(user_message, spots)
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model_name = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
            model = genai.GenerativeModel(model_name)
            context = "\n".join([f"{m['role']}: {m['content']}" for m in history[-6:]])
            prompt = f"{system_prompt}\n\n대화기록:\n{context}\n\n사용자 질문:\n{user_message}"
            response = model.generate_content(prompt)
            return (response.text or "").strip() or _fallback_reply(user_message, spots)
        except Exception:
            return _fallback_reply(user_message, spots)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_reply(user_message, spots)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-8:])
        messages.append({"role": "user", "content": user_message})
        response = client.chat.completions.create(model=model_name, messages=messages, temperature=0.7)
        return (response.choices[0].message.content or "").strip() or _fallback_reply(user_message, spots)
    except Exception:
        return _fallback_reply(user_message, spots)
