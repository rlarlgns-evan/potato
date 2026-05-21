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

# Tip 박스와 동일 — iframe·fragment에서도 깨지지 않도록 인라인
BOX_STYLE = (
    "background:#fff;border-radius:18px;padding:1rem 1.1rem;"
    "box-shadow:0 6px 20px rgba(13,148,136,0.08);border:1px solid #CCFBF1;"
    "min-height:152px;box-sizing:border-box;"
)
LBL_STYLE = (
    f"margin:0 0 0.65rem 0;font-size:0.72rem;font-weight:700;color:{TEAL_DARK};"
    "text-transform:uppercase;font-family:'Plus Jakarta Sans',sans-serif;"
)
SUB_STYLE = (
    "margin:0.5rem 0 0;font-size:0.78rem;color:#64748B;line-height:1.55;"
    "font-family:'Plus Jakarta Sans',sans-serif;"
)


def inject_styles() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
.stApp {{
  background: linear-gradient(180deg, #ECFDF5 0%, #F0FDFA 35%, #F8FAFC 100%);
}}
.block-container {{ padding-top: 1.25rem; max-width: 1080px; }}
#MainMenu, footer, header {{ visibility: hidden; }}

h1, h2, h3, h4 {{ color: #134E4A !important; letter-spacing: -0.02em; }}
.stCaption {{ color: #64748B !important; }}

div[data-testid="stTextInput"] input {{
  border-radius: 14px !important; border: 1px solid #CCFBF1 !important;
  padding: 0.65rem 1rem !important; background: #fff !important;
}}
div[data-testid="stTextInput"] input:focus {{
  border-color: {TEAL} !important; box-shadow: 0 0 0 3px rgba(20,184,166,0.15) !important;
}}
div.stButton > button[kind="secondary"] {{
  background: #fff !important; color: #475569 !important;
  border: 1px solid #E2E8F0 !important; border-radius: 12px !important;
  font-weight: 600 !important;
}}
div.stLinkButton > a {{
  border-radius: 10px !important; font-size: 0.8rem !important;
}}

.app-top {{
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 1.1rem; padding: 0.65rem 0.85rem;
  background: rgba(255,255,255,0.75); backdrop-filter: blur(8px);
  border-radius: 16px; border: 1px solid rgba(204,251,241,0.9);
  box-shadow: 0 4px 20px rgba(13, 148, 136, 0.08);
}}
.app-top .brand {{
  font-size: 1.05rem; font-weight: 800; letter-spacing: 0.06em;
  background: linear-gradient(135deg, {TEAL_DARK}, {TEAL});
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}}

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
  background: linear-gradient(135deg, #0F766E 0%, {TEAL_DARK} 40%, {TEAL} 100%);
  border-radius: 24px; padding: 1.5rem 1.65rem; color: #fff;
  margin-bottom: 1.25rem; position: relative; overflow: hidden;
  box-shadow: 0 20px 50px rgba(13, 148, 136, 0.28);
}}
.featured-trip::before {{
  content: ''; position: absolute; right: -30px; top: -40px;
  width: 180px; height: 180px; border-radius: 50%;
  background: rgba(255,255,255,0.12);
}}
.featured-trip::after {{
  content: 'TRIP'; position: absolute; right: 1.2rem; top: 1rem;
  font-size: 3.5rem; font-weight: 800; opacity: 0.08; letter-spacing: 0.1em;
}}
.featured-trip h3 {{ margin: 0 0 0.45rem 0; font-size: 1.35rem; font-weight: 800; position: relative; }}
.featured-trip p {{ margin: 0; opacity: 0.92; font-size: 0.9rem; line-height: 1.55; position: relative; }}

.section-head {{
  margin: 0 0 0.35rem 0; font-size: 1.05rem; font-weight: 800; color: #134E4A;
}}
.section-sub {{ margin: 0 0 1rem 0; font-size: 0.82rem; color: #64748B; }}

/* MY TRIP — 일정 카드 (HTML) + 투명 클릭 레이어 */
div[data-testid="stVerticalBlock"]:has(.trip-card-visual) {{
  position: relative !important;
  margin-bottom: 0.75rem !important;
}}
div[data-testid="stVerticalBlock"]:has(.trip-card-visual) div[data-testid="stButton"] {{
  position: absolute !important; inset: 0 !important; z-index: 5 !important;
  margin: 0 !important; height: 100% !important;
}}
div[data-testid="stVerticalBlock"]:has(.trip-card-visual) div[data-testid="stButton"] > button {{
  width: 100% !important; height: 100% !important; min-height: 100% !important;
  opacity: 0 !important; border: none !important; background: transparent !important;
  padding: 0 !important; cursor: pointer !important;
}}

.trip-card-visual {{
  position: relative; border-radius: 20px; overflow: hidden;
  background: #fff; border: 1px solid #E2E8F0;
  box-shadow: 0 4px 18px rgba(15, 23, 42, 0.06);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}}
.trip-card-visual.is-active {{
  border-color: {TEAL};
  box-shadow: 0 12px 32px rgba(20, 184, 166, 0.22);
  transform: translateY(-2px);
}}
.trip-card-glow {{
  position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: linear-gradient(180deg, {TEAL}, #2DD4BF);
  opacity: 0; transition: opacity 0.2s;
}}
.trip-card-visual.is-active .trip-card-glow {{ opacity: 1; }}
.trip-card-inner {{ padding: 1.1rem 1.2rem 1rem; }}
.trip-card-head {{
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 0.55rem;
}}
.trip-num {{
  font-size: 1.5rem; font-weight: 800; color: #E2E8F0; line-height: 1;
  font-variant-numeric: tabular-nums;
}}
.trip-card-visual.is-active .trip-num {{ color: {TEAL}; }}
.trip-pill {{
  font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; color: {TEAL_DARK}; background: #F0FDFA;
  border: 1px solid #CCFBF1; padding: 0.2rem 0.55rem; border-radius: 999px;
}}
.trip-title {{
  margin: 0 0 0.35rem; font-size: 1.05rem; font-weight: 800; color: #134E4A;
  line-height: 1.3;
}}
.trip-meta {{ margin: 0 0 0.5rem; font-size: 0.78rem; color: #64748B; }}
.trip-why {{
  margin: 0 0 0.45rem; font-size: 0.86rem; color: #334155; line-height: 1.55;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}}
.trip-move {{
  margin: 0 0 0.55rem; font-size: 0.78rem; color: {TEAL_DARK};
  background: #F0FDFA; border-radius: 10px; padding: 0.35rem 0.55rem;
}}
.trip-tap-hint {{
  display: inline-block; font-size: 0.72rem; font-weight: 700; color: {TEAL};
}}
.trip-ext-link {{
  display: inline-block; margin-left: 0.65rem; font-size: 0.72rem;
  color: #64748B; text-decoration: none; pointer-events: auto; position: relative; z-index: 6;
}}
.trip-ext-link:hover {{ color: {TEAL_DARK}; text-decoration: underline; }}

.trip-info-box {{
  background: #fff; border-radius: 20px; padding: 1.25rem 1.35rem;
  border: 1px solid #E2E8F0; margin-top: 1rem;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
}}
.trip-info-box h4 {{
  margin: 0 0 0.65rem 0; color: {TEAL_DARK}; font-size: 0.8rem;
  text-transform: uppercase; letter-spacing: 0.08em;
}}

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

.dash-box {{
  background: #fff; border-radius: 18px; padding: 1rem 1.1rem;
  box-shadow: 0 6px 20px rgba(13, 148, 136, 0.08);
  border: 1px solid #CCFBF1; min-height: 150px;
  width: 100%; box-sizing: border-box; margin: 0 0 1rem 0;
}}
.dash-box .dash-label {{
  font-size: 0.72rem; font-weight: 700; color: {TEAL_DARK};
  text-transform: uppercase; margin: 0 0 0.65rem 0;
}}
.dash-box .dash-sub {{
  font-size: 0.78rem; color: #64748B; margin: 0; line-height: 1.55;
}}

.dash-inner {{ display: flex; align-items: center; gap: 0.75rem; }}
.dash-inner .w-city {{ font-size: 0.95rem; font-weight: 700; color: #134E4A; margin: 0; }}
.dash-inner .w-temp {{ font-size: 1.2rem; font-weight: 800; color: {TEAL_DARK}; margin: 0.15rem 0 0; }}
.dash-inner .w-meta {{ font-size: 0.78rem; color: #64748B; margin: 0; }}
.dash-dots {{ display: flex; gap: 0.3rem; margin-top: 0.55rem; }}
.dash-dots span {{
  width: 6px; height: 6px; border-radius: 50%; background: #E2E8F0;
}}
.dash-dots span.active {{ background: {TEAL}; }}

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
  <span class="brand">SHY POTATOES · GANGWON</span>
  <span style="font-size:0.72rem;font-weight:700;color:#64748B;letter-spacing:0.12em;">TRAVEL</span>
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


def _icon_thumb_html(icon: str, thumb_bg: str) -> str:
    return (
        f'<div style="flex-shrink:0;width:52px;height:52px;border-radius:14px;display:flex;'
        f"align-items:center;justify-content:center;font-size:1.35rem;font-weight:800;"
        f'color:#fff;background:{thumb_bg};">{html.escape(icon)}</div>'
    )


def _build_festival_rows_html() -> str:
    festivals = get_festivals()
    rows = []
    grads = [
        "linear-gradient(135deg,#0D9488,#14B8A6)",
        "linear-gradient(135deg,#0891B2,#22D3EE)",
        "linear-gradient(135deg,#0284C7,#38BDF8)",
        "linear-gradient(135deg,#7C3AED,#A78BFA)",
    ]
    for i, f in enumerate(festivals):
        icon = FESTIVAL_ICONS[i % len(FESTIVAL_ICONS)]
        rows.append(
            f'<div style="display:flex;align-items:center;gap:10px;padding:6px 0;">'
            f"{_icon_thumb_html(icon, grads[i % 4])}"
            f'<div><strong style="display:block;font-size:0.8rem;color:#134E4A;">'
            f"{html.escape(f['title'])}</strong>"
            f'<span style="font-size:0.72rem;color:#64748B;">'
            f"{html.escape(f['place'])} · {html.escape(f['period'])}</span></div></div>"
        )
    return "".join(rows) * 2


def render_gangwon_dashboard() -> None:
    cities = _cached_weather_cities()
    cities_json = json.dumps(cities, ensure_ascii=False)
    fest_html = _build_festival_rows_html()
    tip_text = "AI가 <b>강원도 전역</b> 관광지에서 맞춤 동선을 골라 드려요."

    html_page = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 0; background: transparent;
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .grid {{
    display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; width: 100%;
  }}
  .box {{ {BOX_STYLE} }}
  .lbl {{ {LBL_STYLE} }}
  .sub {{ {SUB_STYLE} }}
  .w-row {{ display: flex; align-items: center; gap: 12px; }}
  .w-city {{ margin: 0; font-size: 0.95rem; font-weight: 700; color: #134E4A; }}
  .w-temp {{ margin: 4px 0 0; font-size: 1.2rem; font-weight: 800; color: {TEAL_DARK}; }}
  .w-meta {{ margin: 0; font-size: 0.78rem; color: #64748B; }}
  .dots {{ display: flex; gap: 3px; align-items: center; margin-top: 10px; }}
  .dots i {{
    width: 14px; height: 14px; padding: 0; margin: 0; border: none;
    display: inline-flex; align-items: center; justify-content: center;
    font-style: normal; cursor: pointer; background: transparent;
  }}
  .dots i::before {{
    content: ''; width: 6px; height: 6px; border-radius: 50%;
    background: #E2E8F0; display: block;
  }}
  .dots i.on::before {{ background: {TEAL}; }}
  .dots i:hover::before {{ background: #94A3B8; }}
  .dots i.on:hover::before {{ background: {TEAL}; }}
  .fest-vp {{ height: 108px; overflow: hidden; position: relative; }}
  .fest-vp::after {{
    content: ''; position: absolute; left: 0; right: 0; bottom: 0; height: 22px;
    background: linear-gradient(transparent, #fff);
  }}
  .fest-tr {{ animation: scrollUp 22s linear infinite; }}
  .fest-tr:hover {{ animation-play-state: paused; }}
  @keyframes scrollUp {{
    0% {{ transform: translateY(0); }}
    100% {{ transform: translateY(-50%); }}
  }}
</style>
</head>
<body>
<div class="grid">
  <div class="box">
    <p class="lbl">Weather</p>
    <div id="wx-body"></div>
    <div class="dots" id="wx-dots"></div>
  </div>
  <div class="box">
    <p class="lbl">Festival</p>
    <div class="fest-vp"><div class="fest-tr">{fest_html}</div></div>
  </div>
  <div class="box">
    <p class="lbl">Tip</p>
    <p class="sub">{tip_text}</p>
  </div>
</div>
<script>
const cities = {cities_json};
const WX_MS = 3000;
let wi = 0;
let wxTimer = null;

function thumb(bg, icon) {{
  return '<div style="flex-shrink:0;width:52px;height:52px;border-radius:14px;display:flex;'
    + 'align-items:center;justify-content:center;font-size:1.35rem;font-weight:800;color:#fff;background:'
    + bg + ';">' + icon + '</div>';
}}

function renderWeatherAt(idx) {{
  const c = cities[idx];
  let meta = c.label || '';
  if (c.temp_range) meta += ' · ' + c.temp_range;
  document.getElementById('wx-body').innerHTML =
    '<div class="w-row">' + thumb(c.thumb_bg, c.icon) +
    '<div><p class="w-city">' + c.city + '</p>' +
    '<p class="w-temp">' + c.temp_display + '</p>' +
    '<p class="w-meta">' + meta + '</p></div></div>' +
    '<p class="sub">' + (c.tip || '') + '</p>';
  document.getElementById('wx-dots').innerHTML = cities.map((_, j) =>
    '<i class="' + (j === idx ? 'on' : '') + '" data-idx="' + j + '" role="button" '
    + 'aria-label="' + cities[j].city + '"></i>').join('');
  document.querySelectorAll('#wx-dots i').forEach((dot) => {{
    dot.addEventListener('click', () => goToWeather(parseInt(dot.dataset.idx, 10)));
  }});
}}

function advanceWeather() {{
  if (!cities.length) {{
    document.getElementById('wx-body').innerHTML = '<p class="sub">날씨를 불러오지 못했습니다.</p>';
    return;
  }}
  renderWeatherAt(wi);
  wi = (wi + 1) % cities.length;
}}

function goToWeather(idx) {{
  if (!cities.length || idx < 0 || idx >= cities.length) return;
  wi = idx;
  renderWeatherAt(wi);
  wi = (wi + 1) % cities.length;
  resetWeatherTimer();
}}

function resetWeatherTimer() {{
  if (wxTimer) clearInterval(wxTimer);
  wxTimer = setInterval(advanceWeather, WX_MS);
}}

advanceWeather();
resetWeatherTimer();
</script>
</body>
</html>
    """
    components.html(html_page, height=178, scrolling=False)

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


def _trip_card_html(step: dict, spot: dict, active: bool) -> str:
    order = int(step["order"])
    active_cls = " is-active" if active else ""
    stay = step.get("stay_minutes")
    stay_txt = f" · 약 {stay}분" if stay else ""
    theme = html.escape(step.get("theme", "") or "여행")
    move = (step.get("move_to_next") or "").strip()
    move_html = (
        f'<p class="trip-move">🚗 {html.escape(move)}</p>' if move else ""
    )
    ext = ""
    if spot:
        url = f"https://map.kakao.com/link/map/{spot['name']},{spot['lat']},{spot['lng']}"
        ext = (
            f'<a class="trip-ext-link" href="{html.escape(url, quote=True)}" '
            f'target="_blank" rel="noopener">카카오맵 ↗</a>'
        )
    return f"""
<div class="trip-card-visual{active_cls}">
  <div class="trip-card-glow"></div>
  <div class="trip-card-inner">
    <div class="trip-card-head">
      <span class="trip-num">{order:02d}</span>
      <span class="trip-pill">{theme}</span>
    </div>
    <h3 class="trip-title">{html.escape(step['spot_name'])}</h3>
    <p class="trip-meta">{html.escape(step.get('region', ''))}{html.escape(stay_txt)}</p>
    <p class="trip-why">{html.escape(step.get('why', ''))}</p>
    {move_html}
    <span class="trip-tap-hint">탭하여 지도에서 보기</span>{ext}
  </div>
</div>"""


def render_clickable_spot_card(
    step: dict,
    spot: dict,
    active: bool,
    on_click,
) -> None:
    """카드 UI + 투명 버튼 오버레이로 전체 박스 클릭."""
    order = int(step["order"])
    st.markdown(_trip_card_html(step, spot, active), unsafe_allow_html=True)
    st.button(
        "select",
        key=f"spot_card_{order}",
        on_click=on_click,
        args=(order,),
        label_visibility="collapsed",
        type="primary" if active else "secondary",
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
