"""STAR TRAVEL 스타일 · 틸(teal) 테마 UI."""

import html
import json

import streamlit as st
import streamlit.components.v1 as components

from gangwon_content import (
    FESTIVAL_ICONS,
    get_festivals,
    get_highlights,
    get_region_intro,
    get_weather_cities,
)

TEAL = "#14B8A6"
TEAL_DARK = "#0D9488"


def inject_styles() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
.stApp {{ background: #F0FDFA; }}
.block-container {{ padding-top: 1rem; max-width: 1100px; }}
#MainMenu, footer, header {{ visibility: hidden; }}

.app-top {{
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 1rem; font-weight: 800; color: {TEAL_DARK};
}}
.app-top .brand {{ font-size: 1.1rem; letter-spacing: 0.04em; }}

.search-hero {{
  background: linear-gradient(145deg, {TEAL_DARK} 0%, {TEAL} 55%, #2DD4BF 100%);
  border-radius: 22px; padding: 1.5rem 1.6rem; color: #fff;
  box-shadow: 0 16px 40px rgba(13, 148, 136, 0.35);
  margin-bottom: 1.25rem;
}}
.search-hero h2 {{ margin: 0 0 0.35rem 0; font-size: 1.5rem; font-weight: 800; }}
.search-hero p {{ margin: 0 0 1rem 0; opacity: 0.92; font-size: 0.9rem; }}

.info-grid {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem;
  margin-bottom: 1.25rem;
}}
@media (max-width: 768px) {{ .info-grid {{ grid-template-columns: 1fr; }} }}

.info-card {{
  background: #fff; border-radius: 18px; padding: 1rem 1.1rem;
  box-shadow: 0 6px 20px rgba(13, 148, 136, 0.08);
  border: 1px solid #CCFBF1;
}}
.info-card .label {{ font-size: 0.72rem; font-weight: 700; color: {TEAL_DARK}; text-transform: uppercase; }}
.info-card .value {{ font-size: 1rem; font-weight: 700; color: #134E4A; margin: 0.25rem 0; }}
.info-card .sub {{ font-size: 0.78rem; color: #64748B; margin: 0; }}

.highlight-scroll {{
  display: flex; gap: 0.75rem; overflow-x: auto; padding-bottom: 0.5rem; margin-bottom: 1.25rem;
}}
.ui-icon-thumb {{
  flex-shrink: 0;
  width: 52px; height: 52px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.45rem; font-weight: 800; color: #fff;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
}}

.highlight-card {{
  flex: 0 0 200px; border-radius: 18px; padding: 1.1rem; color: #fff;
  min-height: 100px; display: flex; flex-direction: column; justify-content: flex-end;
}}
.highlight-card .ui-icon-thumb {{ margin-bottom: 0.5rem; width: 44px; height: 44px; font-size: 1.2rem; }}
.highlight-card strong {{ font-size: 0.95rem; }}
.highlight-card span {{ font-size: 0.75rem; opacity: 0.9; }}

.festival-list {{ margin: 0; padding: 0; list-style: none; }}
.festival-list li {{
  font-size: 0.8rem; color: #475569; padding: 0.35rem 0;
  border-bottom: 1px solid #F1F5F9;
}}

.screen-steps {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }}
.screen-step {{
  padding: 0.45rem 0.95rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600;
  background: #fff; color: #94A3B8; border: 2px solid #E2E8F0;
}}
.screen-step.active {{
  background: linear-gradient(135deg, {TEAL_DARK}, {TEAL});
  color: #fff; border-color: transparent;
}}
.screen-step.done {{ background: #CCFBF1; color: {TEAL_DARK}; border-color: #99F6E4; }}
.screen-step-line {{ width: 24px; height: 2px; background: #E2E8F0; }}
.screen-step-line.done {{ background: #5EEAD4; }}

.featured-trip {{
  background: linear-gradient(145deg, {TEAL_DARK}, {TEAL});
  border-radius: 22px; padding: 1.35rem 1.5rem; color: #fff;
  margin-bottom: 1rem; position: relative; overflow: hidden;
}}
.featured-trip h3 {{ margin: 0 0 0.5rem 0; font-size: 1.25rem; }}
.featured-trip p {{ margin: 0; opacity: 0.9; font-size: 0.88rem; line-height: 1.5; }}

.spot-pick {{
  background: #fff; border-radius: 18px; padding: 1rem 1.1rem;
  border: 2px solid #E2E8F0; margin-bottom: 0.65rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}}
.spot-pick.active {{
  border-color: {TEAL};
  box-shadow: 0 8px 24px rgba(20, 184, 166, 0.2);
}}
.spot-pick .order {{
  display: inline-block; background: {TEAL}; color: #fff;
  font-weight: 800; font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 8px;
}}

.trip-info-box {{
  background: #fff; border-radius: 18px; padding: 1.2rem;
  border: 1px solid #CCFBF1; margin-top: 1rem;
}}
.trip-info-box h4 {{ margin: 0 0 0.5rem 0; color: {TEAL_DARK}; }}

.map-shell {{
  background: #fff; border-radius: 20px; padding: 0.6rem;
  box-shadow: 0 10px 30px rgba(13, 148, 136, 0.1); border: 1px solid #CCFBF1;
}}
.map-shell .map-label {{ padding: 0.4rem 0.6rem; font-weight: 700; color: #134E4A; }}

div.stButton > button[kind="primary"] {{
  background: linear-gradient(135deg, {TEAL_DARK}, {TEAL}) !important;
  border: none !important; border-radius: 12px !important; font-weight: 700 !important;
}}

.kto-badge {{
  font-size: 0.72rem; color: #64748B; background: #F0FDFA;
  border: 1px dashed #99F6E4; border-radius: 10px; padding: 0.5rem 0.75rem;
  margin-top: 0.75rem;
}}

.dash-grid {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem;
  margin-bottom: 1.25rem;
}}
@media (max-width: 900px) {{ .dash-grid {{ grid-template-columns: 1fr; }} }}

.dash-box {{
  background: #fff; border-radius: 18px; padding: 1rem 1.1rem;
  box-shadow: 0 6px 20px rgba(13, 148, 136, 0.08);
  border: 1px solid #CCFBF1; min-height: 150px;
}}
.dash-box .dash-label {{
  font-size: 0.72rem; font-weight: 700; color: {TEAL_DARK};
  text-transform: uppercase; margin: 0 0 0.65rem 0;
}}
.dash-box .dash-sub {{
  font-size: 0.78rem; color: #64748B; margin: 0; line-height: 1.55;
}}

.weather-slide {{
  display: none; align-items: center; gap: 0.75rem;
  animation: fadeIn 0.4s ease;
}}
.weather-slide.active {{ display: flex; }}
@keyframes fadeIn {{
  from {{ opacity: 0; }} to {{ opacity: 1; }}
}}
.weather-slide .w-city {{ font-size: 0.95rem; font-weight: 700; color: #134E4A; margin: 0; }}
.weather-slide .w-temp {{ font-size: 1.2rem; font-weight: 800; color: {TEAL_DARK}; margin: 0.15rem 0 0; }}
.weather-slide .w-meta {{ font-size: 0.78rem; color: #64748B; margin: 0; }}
.weather-slide .w-tip {{ font-size: 0.76rem; color: #475569; margin: 0.35rem 0 0; line-height: 1.45; }}
.weather-dots {{ display: flex; gap: 0.3rem; margin-top: 0.5rem; }}
.weather-dots span {{
  width: 6px; height: 6px; border-radius: 50%; background: #E2E8F0;
}}
.weather-dots span.active {{ background: {TEAL}; }}

.fest-viewport {{ height: 118px; overflow: hidden; position: relative; }}
.fest-viewport::after {{
  content: ''; position: absolute; left: 0; right: 0; bottom: 0; height: 24px;
  background: linear-gradient(transparent, #fff); pointer-events: none;
}}
.fest-track {{ animation: festScrollUp 24s linear infinite; }}
.fest-track:hover {{ animation-play-state: paused; }}
@keyframes festScrollUp {{
  0% {{ transform: translateY(0); }}
  100% {{ transform: translateY(-50%); }}
}}
.fest-row {{
  display: flex; align-items: center; gap: 0.65rem; padding: 0.45rem 0;
}}
.fest-row strong {{ display: block; font-size: 0.8rem; color: #134E4A; }}
.fest-row span {{ font-size: 0.72rem; color: #64748B; }}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header() -> None:
    st.markdown(
        """
<div class="app-top">
  <span class="brand">🥔 SHY POTATOES TRAVEL</span>
  <span style="font-size:1.2rem;">☰</span>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_screen_steps(active: int) -> None:
    s1 = "active" if active == 1 else ("done" if active > 1 else "")
    s2 = "active" if active == 2 else ""
    line = "done" if active > 1 else ""
    st.markdown(
        f"""
<div class="screen-steps">
  <span class="screen-step {s1}">① 홈 · AI 검색</span>
  <span class="screen-step-line {line}"></span>
  <span class="screen-step {s2}">② MY TRIP · 동선</span>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_home_search_hero() -> None:
    st.markdown(
        f"""
<div class="search-hero">
  <h2>HELLO, TRAVELER</h2>
  <p>{html.escape(get_region_intro())}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=600, show_spinner=False)
def _cached_weather_cities() -> list[dict]:
    return get_weather_cities()


def _icon_thumb(icon: str, thumb_bg: str) -> str:
    return (
        f'<div class="ui-icon-thumb" style="background:{html.escape(thumb_bg)};">'
        f"{html.escape(icon)}</div>"
    )


def _build_weather_slides(cities: list[dict]) -> tuple[str, str]:
    slides_html = []
    dots_html = []
    for i, c in enumerate(cities):
        active = "active" if i == 0 else ""
        thumb = _icon_thumb(c["icon"], c.get("thumb_bg", "linear-gradient(135deg,#CCFBF1,#99F6E4)"))
        tr = c.get("temp_range", "")
        meta = f"{html.escape(c['label'])}"
        if tr:
            meta += f" · {html.escape(tr)}"
        slides_html.append(
            f"""
<div class="weather-slide {active}">
  {thumb}
  <div>
    <p class="w-city">{html.escape(c['city'])}</p>
    <p class="w-temp">{html.escape(c['temp_display'])}</p>
    <p class="w-meta">{meta}</p>
    <p class="w-tip">{html.escape(c.get('tip', ''))}</p>
  </div>
</div>
            """
        )
        dots_html.append(f'<span class="{active}"></span>')
    return "".join(slides_html), "".join(dots_html)


def _build_festival_rows() -> str:
    festivals = get_festivals()
    rows = []
    for i, f in enumerate(festivals):
        icon = FESTIVAL_ICONS[i % len(FESTIVAL_ICONS)]
        grad = [
            "linear-gradient(135deg,#0D9488,#14B8A6)",
            "linear-gradient(135deg,#0891B2,#22D3EE)",
            "linear-gradient(135deg,#0284C7,#38BDF8)",
            "linear-gradient(135deg,#7C3AED,#A78BFA)",
        ][i % 4]
        rows.append(
            f"""
<div class="fest-row">
  {_icon_thumb(icon, grad)}
  <div><strong>{html.escape(f['title'])}</strong><span>{html.escape(f['place'])} · {html.escape(f['period'])}</span></div>
</div>
            """
        )
    return "".join(rows) * 2


def render_gangwon_dashboard() -> None:
    cities = _cached_weather_cities()
    slides_html, dots_html = _build_weather_slides(cities)
    fest_html = _build_festival_rows()
    tip_text = "AI가 강원도 전역 관광지에서 동선을 골라 드려요."

    html_block = f"""
<div class="dash-grid">
  <div class="dash-box">
    <p class="dash-label">Weather</p>
    <div id="weather-slides">{slides_html}</div>
    <div class="weather-dots" id="weather-dots">{dots_html}</div>
  </div>
  <div class="dash-box">
    <p class="dash-label">Festival</p>
    <div class="fest-viewport"><div class="fest-track">{fest_html}</div></div>
  </div>
  <div class="dash-box">
    <p class="dash-label">Tip</p>
    <p class="dash-sub">{html.escape(tip_text)}</p>
  </div>
</div>
<script>
(function() {{
  const slides = document.querySelectorAll('.weather-slide');
  const dots = document.querySelectorAll('#weather-dots span');
  let idx = 0;
  function show(i) {{
    slides.forEach((el, n) => el.classList.toggle('active', n === i));
    dots.forEach((el, n) => el.classList.toggle('active', n === i));
  }}
  setInterval(() => {{ idx = (idx + 1) % slides.length; show(idx); }}, 5000);
}})();
</script>
    """
    components.html(html_block, height=168, scrolling=False)

    highlights = get_highlights()
    cards = []
    for h in highlights:
        cards.append(
            f"""
<div class="highlight-card" style="background:{h.get('gradient', h.get('thumb_bg', '#0D9488'))};">
  <div class="ui-icon-thumb" style="background:rgba(255,255,255,0.25);">{html.escape(h.get('icon', h.get('emoji', '★')))}</div>
  <strong>{html.escape(h['title'])}</strong>
  <span>{html.escape(h['region'])}</span>
</div>
            """
        )
    st.markdown(f'<div class="highlight-scroll">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_featured_trip(spot: dict, meta: dict) -> None:
    title = meta.get("title") or spot["name"]
    summary = meta.get("summary") or spot["description"]
    duration = meta.get("total_duration", "")
    dur = f" · {html.escape(duration)}" if duration else ""
    st.markdown(
        f"""
<div class="featured-trip">
  <h3>{html.escape(title)}</h3>
  <p>{html.escape(summary)}{dur}</p>
  <p style="margin-top:0.75rem;font-size:0.8rem;">📍 {html.escape(spot['region'])} · {html.escape(spot['theme'])}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_spot_pick_card(step: dict, spot: dict, active: bool) -> None:
    cls = "spot-pick active" if active else "spot-pick"
    stay = step.get("stay_minutes")
    stay_txt = f" · 약 {stay}분" if stay else ""
    move = step.get("move_to_next", "")
    move_html = f'<p style="margin:0.5rem 0 0;font-size:0.8rem;color:#0D9488;">🚗 {html.escape(move)}</p>' if move else ""
    st.markdown(
        f"""
<div class="{cls}">
  <span class="order">STEP {step['order']}</span>
  <h4 style="margin:0.5rem 0 0.2rem;color:#134E4A;">{html.escape(step['spot_name'])}</h4>
  <p style="margin:0;font-size:0.78rem;color:#64748B;">{html.escape(step.get('region',''))} · {html.escape(step.get('theme',''))}{html.escape(stay_txt)}</p>
  <p style="margin:0.5rem 0 0;font-size:0.88rem;color:#334155;">{html.escape(step.get('why',''))}</p>
  {move_html}
</div>
        """,
        unsafe_allow_html=True,
    )


def render_trip_information(text: str) -> None:
    st.markdown(
        f"""
<div class="trip-info-box">
  <h4>Trip Information</h4>
  <p style="margin:0;font-size:0.88rem;color:#475569;line-height:1.6;">{html.escape(text)}</p>
  <div class="kto-badge">📡 추후 한국관광공사 Tour API 데이터로 날씨·축제·관광지 정보가 자동 갱신됩니다.</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def map_card_open(title: str) -> None:
    st.markdown(f'<div class="map-shell"><div class="map-label">{html.escape(title)}</div>', unsafe_allow_html=True)


def map_card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
