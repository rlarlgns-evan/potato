"""Travel-app 스타일 UI (Streamlit 커스텀 CSS·카드 컴포넌트)."""

import html
import streamlit as st

THEME_ICONS = {
    "힐링": ("🌲", "#8B5CF6"),
    "야경": ("🌙", "#5B5FEA"),
    "트레킹": ("🥾", "#FF8C42"),
    "역사": ("🏛️", "#FFD166"),
    "체험": ("✨", "#22C55E"),
    "자전거": ("🚲", "#3B82F6"),
}


def inject_styles() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
  font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
}

.stApp {
  background: linear-gradient(180deg, #EEF2FF 0%, #F8FAFC 45%, #F1F5F9 100%);
}

.block-container {
  padding-top: 1.2rem;
  max-width: 1180px;
}

section[data-testid="stSidebar"] {
  background: #fff;
  border-right: 1px solid #E8ECF4;
}
section[data-testid="stSidebar"] .block-container {
  padding-top: 1.5rem;
}

#MainMenu, footer, header { visibility: hidden; }

.hero-card {
  background: linear-gradient(135deg, #5B5FEA 0%, #7C3AED 55%, #6366F1 100%);
  border-radius: 24px;
  padding: 1.6rem 1.8rem;
  color: #fff;
  box-shadow: 0 20px 50px rgba(91, 95, 234, 0.35);
  margin-bottom: 1rem;
}
.hero-card .eyebrow {
  font-size: 0.85rem;
  opacity: 0.9;
  margin: 0 0 0.25rem 0;
}
.hero-card h1 {
  font-size: 1.75rem;
  font-weight: 800;
  margin: 0 0 0.35rem 0;
  letter-spacing: -0.02em;
}
.hero-card p {
  margin: 0;
  opacity: 0.92;
  font-size: 0.95rem;
}

.surface-card {
  background: #fff;
  border-radius: 20px;
  padding: 1.25rem 1.35rem;
  box-shadow: 0 8px 30px rgba(15, 23, 42, 0.06);
  border: 1px solid #EEF2FF;
  margin-bottom: 1rem;
}
.surface-card h3 {
  margin: 0 0 0.75rem 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #1E293B;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin: 0.5rem 0 1rem 0;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.55rem 1rem;
  border-radius: 14px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #fff;
  box-shadow: 0 6px 16px rgba(0,0,0,0.08);
}

.spot-scroll {
  display: flex;
  gap: 0.85rem;
  overflow-x: auto;
  padding-bottom: 0.5rem;
  margin: 0.5rem 0 1rem 0;
  scrollbar-width: thin;
}
.spot-mini {
  flex: 0 0 168px;
  background: #fff;
  border-radius: 18px;
  padding: 0.85rem;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.07);
  border: 1px solid #EEF2FF;
}
.spot-mini .thumb {
  height: 72px;
  border-radius: 12px;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.8rem;
}
.spot-mini strong {
  display: block;
  font-size: 0.82rem;
  color: #1E293B;
  line-height: 1.3;
}
.spot-mini span {
  font-size: 0.72rem;
  color: #64748B;
}

.ticket-card {
  background: #fff;
  border-radius: 20px;
  padding: 1.1rem 1.25rem;
  margin-bottom: 0.85rem;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.07);
  border: 1px solid #E8ECF8;
  position: relative;
  overflow: hidden;
}
.ticket-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, #5B5FEA, #A78BFA);
}
.ticket-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.5rem;
}
.ticket-order {
  background: linear-gradient(135deg, #5B5FEA, #7C3AED);
  color: #fff;
  font-weight: 800;
  font-size: 0.75rem;
  padding: 0.25rem 0.55rem;
  border-radius: 8px;
}
.ticket-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #0F172A;
  margin: 0.35rem 0 0.15rem 0;
}
.ticket-meta {
  font-size: 0.78rem;
  color: #64748B;
  margin-bottom: 0.5rem;
}
.ticket-body {
  font-size: 0.88rem;
  color: #334155;
  line-height: 1.55;
  margin: 0;
}
.ticket-move {
  margin-top: 0.65rem;
  padding: 0.55rem 0.75rem;
  background: #F0F4FF;
  border-radius: 12px;
  font-size: 0.8rem;
  color: #4338CA;
}

.map-shell {
  background: #fff;
  border-radius: 22px;
  padding: 0.65rem;
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.08);
  border: 1px solid #E8ECF8;
  overflow: hidden;
}
.map-shell .map-label {
  padding: 0.35rem 0.65rem 0.5rem;
  font-weight: 700;
  font-size: 0.95rem;
  color: #1E293B;
}
.map-shell .map-hint {
  padding: 0 0.65rem 0.55rem;
  font-size: 0.78rem;
  color: #64748B;
}

.stat-pill {
  display: inline-block;
  background: #EEF2FF;
  color: #4338CA;
  font-weight: 700;
  font-size: 0.8rem;
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  margin-right: 0.5rem;
}

div[data-testid="stChatMessage"] {
  background: #fff !important;
  border: 1px solid #E8ECF8 !important;
  border-radius: 16px !important;
  box-shadow: 0 4px 14px rgba(15,23,42,0.04) !important;
}

div[data-testid="stChatInput"] > div {
  border-radius: 16px !important;
  border: 2px solid #E0E7FF !important;
  box-shadow: 0 8px 24px rgba(91, 95, 234, 0.12) !important;
}

.stLinkButton > a {
  background: linear-gradient(135deg, #5B5FEA, #6366F1) !important;
  color: white !important;
  border: none !important;
  border-radius: 12px !important;
  font-weight: 600 !important;
}

.step-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #5B5FEA, #7C3AED);
  color: #fff;
  font-weight: 800;
  font-size: 0.8rem;
}

.screen-steps {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}
.screen-step {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 600;
  background: #fff;
  color: #94A3B8;
  border: 2px solid #E2E8F0;
}
.screen-step.active {
  background: linear-gradient(135deg, #5B5FEA, #7C3AED);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 6px 18px rgba(91, 95, 234, 0.35);
}
.screen-step.done {
  background: #EEF2FF;
  color: #4338CA;
  border-color: #C7D2FE;
}
.screen-step-line {
  width: 28px;
  height: 2px;
  background: #E2E8F0;
}
.screen-step-line.done {
  background: #A5B4FC;
}

div.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #5B5FEA, #6366F1) !important;
  border: none !important;
  border-radius: 14px !important;
  font-weight: 700 !important;
  padding: 0.65rem 1.25rem !important;
  box-shadow: 0 10px 24px rgba(91, 95, 234, 0.35) !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_screen_steps(active: int) -> None:
    """active: 1 = 홈(채팅), 2 = 결과(동선·지도)"""
    s1 = "active" if active == 1 else ("done" if active > 1 else "")
    s2 = "active" if active == 2 else ""
    line = "done" if active > 1 else ""
    st.markdown(
        f"""
<div class="screen-steps">
  <span class="screen-step {s1}">① Plan · AI 채팅</span>
  <span class="screen-step-line {line}"></span>
  <span class="screen-step {s2}">② Route · 동선 정보</span>
</div>
        """,
        unsafe_allow_html=True,
    )


def hero_header(screen: int = 1) -> None:
    title = "Find Your Route" if screen == 1 else "Your Trip Plan"
    sub = "AI와 대화하고 취향을 알려주세요" if screen == 1 else "추천 동선과 카카오맵을 확인하세요"
    st.markdown(
        f"""
<div class="hero-card">
  <p class="eyebrow">안녕하세요, 여행자님 👋</p>
  <h1>{html.escape(title)}</h1>
  <p>{html.escape(sub)}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_theme_chips() -> None:
    chips = []
    for name, (icon, color) in THEME_ICONS.items():
        chips.append(
            f'<span class="chip" style="background:{color};">{icon} {html.escape(name)}</span>'
        )
    st.markdown(f'<div class="chip-row">{"".join(chips)}</div>', unsafe_allow_html=True)


def render_spot_carousel(spots: list[dict]) -> None:
    if not spots:
        return
    cards = []
    icons = ["🏔️", "🌲", "🌊", "⭐", "🚲", "🛤️"]
    for i, s in enumerate(spots[:8]):
        icon = icons[i % len(icons)]
        grad = ["#DDD6FE", "#BFDBFE", "#FECACA", "#FDE68A", "#BBF7D0", "#E9D5FF"][i % 6]
        cards.append(
            f"""
<div class="spot-mini">
  <div class="thumb" style="background:{grad};">{icon}</div>
  <strong>{html.escape(s['name'])}</strong>
  <span>{html.escape(s['region'])} · {html.escape(s['theme'])}</span>
</div>
            """
        )
    st.markdown(
        f'<div class="surface-card"><h3>Popular Places</h3><div class="spot-scroll">{"".join(cards)}</div></div>',
        unsafe_allow_html=True,
    )


def render_step_ticket(step: dict, spot: dict | None) -> None:
    stay = step.get("stay_minutes")
    stay_txt = f" · 약 {stay}분" if stay else ""
    move = step.get("move_to_next", "")
    move_html = (
        f'<div class="ticket-move">🚗 {html.escape(move)}</div>' if move else ""
    )
    map_btn = ""
    if spot:
        url = f"https://map.kakao.com/link/map/{spot['name']},{spot['lat']},{spot['lng']}"
        map_btn = f'<a href="{html.escape(url)}" target="_blank" style="font-size:0.78rem;color:#5B5FEA;font-weight:600;">카카오맵 →</a>'

    st.markdown(
        f"""
<div class="ticket-card">
  <div class="ticket-head">
    <span class="ticket-order">STEP {step['order']}</span>
    {map_btn}
  </div>
  <div class="ticket-title">{html.escape(step['spot_name'])}</div>
  <div class="ticket-meta">{html.escape(step.get('region', ''))} · {html.escape(step.get('theme', ''))}{html.escape(stay_txt)}</div>
  <p class="ticket-body">{html.escape(step.get('why', ''))}</p>
  {move_html}
</div>
        """,
        unsafe_allow_html=True,
    )


def section_title(text: str, subtitle: str = "") -> None:
    sub = f'<p style="margin:0;color:#64748B;font-size:0.88rem;">{html.escape(subtitle)}</p>' if subtitle else ""
    st.markdown(
        f'<div style="margin:1rem 0 0.75rem 0;"><h2 style="margin:0;font-size:1.25rem;font-weight:800;color:#0F172A;">{html.escape(text)}</h2>{sub}</div>',
        unsafe_allow_html=True,
    )


def map_card_open(title: str, hint: str) -> None:
    st.markdown(
        f'<div class="map-shell"><div class="map-label">{html.escape(title)}</div><div class="map-hint">{html.escape(hint)}</div>',
        unsafe_allow_html=True,
    )


def map_card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
