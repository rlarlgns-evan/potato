"""VoyageAI · Ethereal Intelligence design system (Streamlit)."""

import html
import json
from typing import Any
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components

from design_tokens import TOKENS as T
from gangwon_content import (
    FESTIVAL_ICONS,
    get_festivals,
    get_highlights,
    get_region_intro,
    get_weather_cities,
)

# Stitch Ethereal Intelligence
PRIMARY = T.primary
PRIMARY_CONTAINER = T.primary_container
PRIMARY_DARK = T.primary
SURFACE = T.background
TEXT = T.on_surface
TEXT_MUTED = T.on_surface_variant
LAVENDER = T.tertiary_fixed
SKY = T.secondary_container
SOFT_ORANGE = "#ffdcc8"
TEAL = T.primary_container
TEAL_DARK = T.primary
GLASS = "rgba(255,255,255,0.85)"
SHADOW = "0 8px 30px rgba(0,106,97,0.08)"

BOX_STYLE = (
    f"background:{GLASS};backdrop-filter:blur(20px);"
    f"border-radius:24px;padding:1rem 1.1rem;"
    f"box-shadow:{SHADOW};border:1px solid rgba(255,255,255,0.9);"
    f"min-height:152px;box-sizing:border-box;"
)
LBL_STYLE = (
    f"margin:0 0 0.65rem 0;font-size:12px;font-weight:700;color:{TEXT_MUTED};"
    "text-transform:uppercase;letter-spacing:0.05em;font-family:Inter,sans-serif;"
)
SUB_STYLE = (
    f"margin:0.5rem 0 0;font-size:14px;color:{TEXT_MUTED};line-height:1.5;"
    "font-family:Inter,sans-serif;"
)


def inject_styles() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', system-ui, sans-serif; }}
.stApp {{
  background: {SURFACE};
  background-image:
    radial-gradient(ellipse 80% 50% at 10% -10%, rgba(0,106,97,0.1), transparent),
    radial-gradient(ellipse 60% 40% at 95% 5%, rgba(136,214,253,0.28), transparent),
    radial-gradient(ellipse 50% 30% at 50% 100%, rgba(230,222,255,0.22), transparent);
}}
.block-container {{ padding-top: 1rem; max-width: 1120px; }}
#MainMenu, footer, header {{ visibility: hidden; }}

h1, h2, h3, h4 {{ color: {TEXT} !important; letter-spacing: -0.03em; }}
.stCaption {{ color: {TEXT_MUTED} !important; }}

div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {{
  border-radius: 16px !important; border: 1px solid rgba(102,188,176,0.25) !important;
  padding: 0.7rem 1rem !important;
  background: rgba(255,255,255,0.85) !important; backdrop-filter: blur(8px);
}}
div[data-testid="stTextInput"] input:focus {{
  border-color: {PRIMARY} !important;
  box-shadow: 0 0 0 3px rgba(102,188,176,0.2) !important;
}}
div.stButton > button[kind="secondary"] {{
  background: rgba(255,255,255,0.9) !important; color: {TEXT} !important;
  border: 1px solid rgba(102,188,176,0.2) !important;
  border-radius: 14px !important; font-weight: 600 !important;
}}
div.stButton > button[kind="primary"] {{
  background: linear-gradient(180deg, {PRIMARY} 0%, #005a52 100%) !important;
  color: {T.on_primary} !important; border: none !important;
  border-radius: 999px !important; font-weight: 600 !important;
  box-shadow: 0 4px 16px rgba(0,106,97,0.28) !important;
}}
div.stButton > button[kind="primary"]:hover {{
  filter: brightness(1.05);
}}
div.stLinkButton > a {{
  border-radius: 14px !important; font-size: 0.82rem !important;
  border: 1px solid rgba(102,188,176,0.25) !important;
}}

.app-top {{
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 1rem; padding: 0.75rem 1rem;
  background: rgba(255,255,255,0.65); backdrop-filter: blur(16px);
  border-radius: 24px; border: 1px solid rgba(255,255,255,0.8);
  box-shadow: 0 4px 24px rgba(102,188,176,0.1);
}}
.app-top .brand {{
  font-size: 1rem; font-weight: 800; letter-spacing: -0.02em; color: {TEXT};
}}
.app-top .brand span {{ color: {PRIMARY_DARK}; }}
.app-top .tag {{
  font-size: 0.65rem; font-weight: 700; letter-spacing: 0.12em;
  color: {PRIMARY_DARK}; background: rgba(102,188,176,0.15);
  padding: 0.3rem 0.6rem; border-radius: 999px;
}}

.vx-chat-shell {{
  max-width: 640px; margin: 0 auto 1.25rem;
  background: rgba(255,255,255,0.7); backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.9); border-radius: 24px;
  padding: 1.5rem 1.6rem; box-shadow: 0 8px 32px rgba(102,188,176,0.12);
}}
.vx-chat-shell h2 {{
  margin: 0 0 0.35rem; font-size: 1.35rem; font-weight: 800;
  color: {TEXT} !important; letter-spacing: -0.03em;
}}
.vx-chat-shell p {{ margin: 0; font-size: 0.9rem; color: {TEXT_MUTED}; line-height: 1.6; }}
.vx-chat-hint {{
  margin-top: 0.85rem; font-size: 0.75rem; color: {TEXT_MUTED};
  text-align: center;
}}

.search-hero {{
  background: rgba(255,255,255,0.55); backdrop-filter: blur(12px);
  border-radius: 24px; padding: 1.25rem 1.4rem; margin-bottom: 1rem;
  border: 1px solid rgba(102,188,176,0.15);
  box-shadow: 0 4px 20px rgba(102,188,176,0.08);
}}
.search-hero h2 {{ margin: 0 0 0.35rem 0; font-size: 1.2rem; font-weight: 700; color: {TEXT} !important; }}
.search-hero p {{ margin: 0; font-size: 0.88rem; color: {TEXT_MUTED}; }}

.info-grid {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem;
  margin-bottom: 1.25rem;
}}
@media (max-width: 768px) {{ .info-grid {{ grid-template-columns: 1fr; }} }}

.info-card {{
  background: rgba(255,255,255,0.72); backdrop-filter: blur(12px);
  border-radius: 24px; padding: 1rem 1.1rem;
  box-shadow: 0 4px 24px rgba(102,188,176,0.1);
  border: 1px solid rgba(102,188,176,0.15);
}}
.info-card .label {{ font-size: 0.72rem; font-weight: 700; color: {PRIMARY_DARK}; text-transform: uppercase; }}
.info-card .value {{ font-size: 1rem; font-weight: 700; color: {TEXT}; margin: 0.25rem 0; }}
.info-card .sub {{ font-size: 0.78rem; color: {TEXT_MUTED}; margin: 0; }}

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
  flex: 0 0 200px; border-radius: 24px; padding: 1.1rem; color: #fff;
  min-height: 100px; display: flex; flex-direction: column; justify-content: flex-end;
  transition: transform 0.2s ease; cursor: default;
}}
.highlight-card:hover {{ transform: scale(1.02); }}
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
  padding: 0.4rem 0.9rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600;
  background: rgba(255,255,255,0.6); color: {TEXT_MUTED};
  border: 1px solid rgba(102,188,176,0.15);
}}
.screen-step.active {{
  background: {PRIMARY}; color: #fff; border-color: transparent;
  box-shadow: 0 4px 12px rgba(102,188,176,0.35);
}}
.screen-step.done {{ background: rgba(102,188,176,0.12); color: {PRIMARY_DARK}; border-color: rgba(102,188,176,0.25); }}
.screen-step-line {{ width: 20px; height: 2px; background: rgba(102,188,176,0.2); border-radius: 2px; }}
.screen-step-line.done {{ background: {PRIMARY}; }}

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

/* MY TRIP — Phase 2 split-view (VoyageAI) */
.vx-split-label {{
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: {PRIMARY_DARK}; margin: 0 0 0.75rem;
}}
.mt-hero {{
  background: rgba(255,255,255,0.72); backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,0.9); border-radius: 24px;
  padding: 1.35rem 1.45rem; margin-bottom: 1.15rem;
  box-shadow: 0 8px 32px rgba(102,188,176,0.1);
}}
.mt-hero-row {{ display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; flex-wrap: wrap; }}
.mt-kicker {{ font-size: 0.68rem; font-weight: 700; letter-spacing: 0.14em; color: {PRIMARY_DARK}; }}
.mt-chip {{
  font-size: 0.72rem; font-weight: 600; color: {TEXT};
  background: rgba(102,188,176,0.12); border-radius: 999px; padding: 0.25rem 0.65rem;
}}
.mt-chip.accent-lav {{ background: {LAVENDER}; color: #5b21b6; }}
.mt-chip.accent-sky {{ background: {SKY}; color: #0369a1; }}
.mt-hero h1 {{ margin: 0.55rem 0 0.4rem; font-size: 1.3rem; font-weight: 800; color: {TEXT} !important; line-height: 1.3; letter-spacing: -0.03em; }}
.mt-hero-summary {{ margin: 0; font-size: 0.88rem; color: {TEXT_MUTED}; line-height: 1.55; }}
.mt-query {{
  margin: 0.75rem 0 0; font-size: 0.78rem; color: {TEXT_MUTED};
  padding: 0.45rem 0.65rem; background: rgba(102,188,176,0.08); border-radius: 12px;
}}

.mt-panel-label {{
  margin: 0 0 0.65rem; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: {TEXT_MUTED};
}}
.vx-theme-tags {{ display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.75rem; }}
.vx-theme-tag {{
  font-size: 0.68rem; font-weight: 600; padding: 0.25rem 0.55rem; border-radius: 999px;
}}
.vx-theme-tag:nth-child(3n+1) {{ background: {SKY}; color: #0369a1; }}
.vx-theme-tag:nth-child(3n+2) {{ background: {LAVENDER}; color: #5b21b6; }}
.vx-theme-tag:nth-child(3n) {{ background: {SOFT_ORANGE}; color: #c2410c; }}

.mytrip-route-block {{ margin-bottom: 0.25rem; }}
div[data-testid="stPills"] [data-baseweb="button-group"] {{
  display: flex !important; flex-direction: column !important;
  width: 100% !important; gap: 0.5rem !important;
}}
div[data-testid="stPills"] [data-baseweb="button-group"] > button {{
  width: 100% !important; min-height: 3.75rem !important; height: auto !important;
  justify-content: flex-start !important; text-align: left !important;
  padding: 0.85rem 1rem !important; border-radius: 20px !important;
  white-space: pre-wrap !important; line-height: 1.45 !important;
  font-size: 0.83rem !important; font-weight: 500 !important;
  background: rgba(255,255,255,0.85) !important; color: {TEXT} !important;
  border: 1px solid rgba(102,188,176,0.15) !important;
  box-shadow: 0 2px 8px rgba(102,188,176,0.06) !important;
  transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}}
div[data-testid="stPills"] [data-baseweb="button-group"] > button:hover {{
  transform: translateY(-1px); box-shadow: 0 4px 16px rgba(102,188,176,0.12) !important;
}}
div[data-testid="stPills"] [data-baseweb="button-group"] > button[aria-pressed="true"] {{
  background: rgba(102,188,176,0.15) !important; color: {PRIMARY_DARK} !important;
  border: 1.5px solid {PRIMARY} !important;
  box-shadow: 0 0 0 3px rgba(102,188,176,0.15) !important;
  font-weight: 600 !important;
}}
.mt-detail {{
  background: rgba(255,255,255,0.8); backdrop-filter: blur(12px);
  border: 1px solid rgba(102,188,176,0.2); border-radius: 24px;
  padding: 1.15rem 1.2rem; margin: 1rem 0 0.85rem;
  box-shadow: 0 8px 28px rgba(102,188,176,0.1);
}}
.mt-detail-top {{ display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; margin-bottom: 0.5rem; }}
.mt-step-badge {{
  font-size: 0.68rem; font-weight: 800; letter-spacing: 0.06em;
  color: #fff; background: {PRIMARY}; padding: 0.25rem 0.55rem; border-radius: 8px;
}}
.mt-theme-chip {{
  font-size: 0.68rem; font-weight: 600; color: {PRIMARY_DARK};
  background: rgba(102,188,176,0.12); padding: 0.2rem 0.55rem; border-radius: 8px;
}}
.mt-detail h2 {{ margin: 0 0 0.35rem; font-size: 1.08rem; font-weight: 800; color: {TEXT} !important; line-height: 1.35; letter-spacing: -0.02em; }}
.mt-detail-meta {{ margin: 0 0 0.75rem; font-size: 0.8rem; color: {TEXT_MUTED}; }}
.vx-ai-why {{
  margin: 0 0 0.65rem; padding: 0.85rem 1rem; border-radius: 16px;
  background: linear-gradient(135deg, rgba(102,188,176,0.1), rgba(186,230,253,0.2));
  border: 1px solid rgba(102,188,176,0.15);
}}
.vx-ai-why-label {{
  font-size: 0.65rem; font-weight: 800; letter-spacing: 0.1em;
  text-transform: uppercase; color: {PRIMARY_DARK}; margin-bottom: 0.35rem;
}}
.vx-ai-why p {{ margin: 0; font-size: 0.86rem; color: {TEXT}; line-height: 1.6; }}
.mt-detail-move {{
  margin: 0.5rem 0 0; padding: 0.55rem 0.7rem; border-radius: 14px;
  background: rgba(255,255,255,0.6); border: 1px solid rgba(102,188,176,0.12);
  font-size: 0.8rem; color: {TEXT_MUTED}; line-height: 1.5;
}}

.mt-map-card {{
  background: rgba(255,255,255,0.72); backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,0.9); border-radius: 24px;
  padding: 0.9rem 1rem; box-shadow: 0 8px 32px rgba(102,188,176,0.1);
}}
.mt-map-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; margin-bottom: 0.65rem; }}
.mt-map-head h3 {{ margin: 0; font-size: 0.92rem; font-weight: 700; color: {TEXT} !important; letter-spacing: -0.02em; }}
.mt-map-head span {{ font-size: 0.75rem; color: {TEXT_MUTED}; }}

.trip-info-box {{
  background: #F8FAFC; border-radius: 14px; padding: 1rem 1.1rem;
  border: 1px solid #F1F5F9; margin-top: 0.5rem;
}}
.trip-info-box h4 {{
  margin: 0 0 0.5rem 0; color: #64748B; font-size: 0.72rem;
  text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700;
}}
.trip-info-box .kto-badge {{ display: none; }}

.map-shell {{
  background: #fff; border-radius: 20px; padding: 0.6rem;
  box-shadow: 0 10px 30px rgba(13, 148, 136, 0.1); border: 1px solid #CCFBF1;
}}
.map-shell .map-label {{ padding: 0.4rem 0.6rem; font-weight: 700; color: #134E4A; }}


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

/* VoyageAI Stitch layout (Ethereal Intelligence) */
.vx-topnav {{
  margin-bottom: 1rem; padding: 0.5rem 0.75rem;
  background: {GLASS}; backdrop-filter: blur(20px);
  border-radius: 24px; border: 1px solid rgba(255,255,255,0.95);
  box-shadow: {SHADOW};
}}
.vx-topnav-grid {{
  display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 1rem;
}}
.vx-topnav .logo {{ font-size: 1.1rem; font-weight: 800; color: {PRIMARY}; letter-spacing: -0.03em; }}
.vx-nav-search {{
  max-width: 360px; margin: 0 auto; width: 100%;
  padding: 0.55rem 1rem 0.55rem 2.25rem; border-radius: 999px;
  background: {T.surface_container_lowest}; border: 1px solid {T.outline_variant};
  font-size: 0.82rem; color: {TEXT_MUTED};
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%236e7977' viewBox='0 0 16 16'%3E%3Cpath d='M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85zm-5.242 1.106a5 5 0 1 1 0-10 5 5 0 0 1 0 10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: 0.75rem center;
}}
.vx-topnav .nav-links {{ display: flex; gap: 1.1rem; justify-content: center; flex-wrap: wrap; }}
.vx-topnav .nav-links span {{ font-size: 0.82rem; font-weight: 600; color: {TEXT_MUTED}; }}
.vx-topnav .nav-links span.on {{ color: {PRIMARY}; border-bottom: 2px solid {PRIMARY_CONTAINER}; padding-bottom: 2px; }}
.vx-topnav .nav-right {{ display: flex; align-items: center; gap: 0.75rem; font-size: 1.05rem; color: {TEXT_MUTED}; justify-content: flex-end; }}

.vx-sidebar {{
  background: {T.inverse_surface};
  border-radius: 24px; padding: 1.1rem 0.85rem; min-height: 520px;
  display: flex; flex-direction: column; box-shadow: {SHADOW};
}}
.vx-sidebar .sb-logo {{ font-size: 1rem; font-weight: 800; color: #fff; margin-bottom: 1.25rem; padding: 0 0.35rem; }}
.vx-sidebar .sb-item {{
  display: flex; align-items: center; gap: 0.55rem; padding: 0.55rem 0.65rem;
  border-radius: 12px; font-size: 0.8rem; font-weight: 600; color: rgba(255,255,255,0.55);
  margin-bottom: 0.25rem;
}}
.vx-sidebar .sb-item.on {{ background: {PRIMARY}; color: {T.on_primary}; }}
.vx-sidebar .sb-foot {{ margin-top: auto; padding-top: 1rem; color: #f87171; font-size: 0.78rem; font-weight: 600; }}

.vx-welcome {{
  background: linear-gradient(135deg, {SKY} 0%, {T.surface_container_low} 45%, {SURFACE} 100%);
  border-radius: 24px; padding: 1.35rem 1.5rem; margin-bottom: 1rem;
  border: 1px solid rgba(255,255,255,0.8); box-shadow: {SHADOW};
}}
.vx-welcome h2 {{
  margin: 0 0 0.4rem; font-size: 1.25rem; font-weight: 700; color: {TEXT} !important;
  letter-spacing: -0.02em; text-transform: uppercase;
}}
.vx-welcome p {{ margin: 0; font-size: 0.88rem; color: {TEXT_MUTED}; line-height: 1.6; }}

.vx-profile {{
  background: rgba(255,255,255,0.75); backdrop-filter: blur(12px);
  border-radius: 24px; padding: 1.15rem; border: 1px solid rgba(255,255,255,0.9);
  box-shadow: 0 4px 20px rgba(102,188,176,0.08);
}}
.vx-profile .avatar {{
  width: 56px; height: 56px; border-radius: 50%;
  background: linear-gradient(135deg, {PRIMARY}, #7dd3fc); margin-bottom: 0.5rem;
}}
.vx-profile h4 {{ margin: 0; font-size: 0.95rem; font-weight: 800; color: {TEXT} !important; }}
.vx-profile .elite {{ font-size: 0.65rem; font-weight: 700; color: {PRIMARY_DARK}; letter-spacing: 0.08em; }}
.vx-stat-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin: 0.75rem 0; }}
.vx-stat {{ background: #f8fafc; border-radius: 12px; padding: 0.5rem; text-align: center; }}
.vx-stat strong {{ display: block; font-size: 1rem; color: {TEXT}; }}
.vx-stat span {{ font-size: 0.65rem; color: {TEXT_MUTED}; text-transform: uppercase; }}

.vx-chat-box {{
  background: rgba(255,255,255,0.8); border-radius: 20px; padding: 1rem 1.1rem;
  border: 1px solid rgba(102,188,176,0.12); margin: 1rem 0;
}}
.vx-bubble-ai, .vx-bubble-user {{
  max-width: 92%; padding: 0.75rem 0.9rem; border-radius: 16px; margin-bottom: 0.65rem;
  font-size: 0.84rem; line-height: 1.5;
}}
.vx-bubble-ai {{ background: #fff; color: {TEXT}; border: 1px solid #f1f5f9; }}
.vx-bubble-user {{
  background: {PRIMARY}; color: {T.on_primary}; margin-left: auto;
  border-bottom-right-radius: 4px;
}}
.vx-quick-pills {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }}
.vx-quick-pills span {{
  font-size: 0.72rem; padding: 0.35rem 0.65rem; border-radius: 999px;
  background: #f1f5f9; color: {TEXT_MUTED}; font-weight: 600;
}}

.vx-tailored-head {{ margin-bottom: 1rem; }}
.vx-tailored-head h1 {{ margin: 0 0 0.35rem; font-size: 1.45rem; font-weight: 800; color: {PRIMARY_DARK} !important; letter-spacing: -0.03em; }}
.vx-tailored-head p {{ margin: 0; font-size: 0.84rem; color: {TEXT_MUTED}; max-width: 520px; line-height: 1.55; }}
.vx-head-chips {{ display: flex; gap: 0.4rem; flex-wrap: wrap; justify-content: flex-end; }}
.vx-head-chip {{
  font-size: 0.68rem; font-weight: 700; padding: 0.35rem 0.7rem; border-radius: 999px;
  background: rgba(102,188,176,0.12); color: {PRIMARY_DARK}; border: 1px solid rgba(102,188,176,0.2);
}}

.course-card {{
  background: #fff; border-radius: 20px; overflow: hidden; margin-bottom: 1rem;
  border: 2px solid transparent; box-shadow: 0 4px 20px rgba(15,23,42,0.06);
  transition: border-color 0.15s, box-shadow 0.15s;
}}
.course-card.on {{ border-color: {PRIMARY_CONTAINER}; box-shadow: 0 12px 36px rgba(0,106,97,0.15); }}
.course-card img {{ width: 100%; height: 150px; object-fit: cover; display: block; }}
.course-card-body {{ padding: 0.9rem 1rem 1rem; }}
.course-card-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; }}
.course-card h3 {{ margin: 0; font-size: 0.95rem; font-weight: 800; color: {TEXT} !important; line-height: 1.3; }}
.course-price {{ font-size: 0.72rem; font-weight: 700; color: {PRIMARY_DARK}; white-space: nowrap; }}
.course-loc {{ margin: 0.35rem 0 0.65rem; font-size: 0.75rem; color: {TEXT_MUTED}; }}
.course-badge {{
  position: absolute; top: 12px; right: 12px; font-size: 0.62rem; font-weight: 800;
  letter-spacing: 0.06em; padding: 0.25rem 0.5rem; border-radius: 8px;
  background: rgba(255,255,255,0.92); color: {PRIMARY_DARK};
}}
.course-img-wrap {{ position: relative; }}
.course-ai {{
  background: linear-gradient(135deg, rgba(102,188,176,0.08), rgba(186,230,253,0.15));
  border-radius: 14px; padding: 0.65rem 0.75rem; border: 1px solid rgba(102,188,176,0.12);
}}
.course-ai-label {{ font-size: 0.62rem; font-weight: 800; color: {PRIMARY_DARK}; letter-spacing: 0.08em; margin-bottom: 0.25rem; }}
.course-ai p {{ margin: 0; font-size: 0.78rem; color: {TEXT}; line-height: 1.5; }}

/* Planner: 일정 카드 = 전체 너비 버튼 (st-key-course_pick_N) */
div[class*="st-key-course_pick_"] button {{
  min-height: 11.25rem !important; height: auto !important; width: 100% !important;
  white-space: pre-wrap !important; text-align: left !important;
  justify-content: flex-start !important; align-items: flex-end !important;
  padding: 6.25rem 1rem 1rem !important; border-radius: 20px !important;
  margin-bottom: 0.15rem !important; color: #fff !important;
  text-shadow: 0 1px 4px rgba(0,0,0,0.55); line-height: 1.45 !important;
  font-size: 0.83rem !important; font-weight: 500 !important;
  border: 1px solid rgba(255,255,255,0.2) !important;
  box-shadow: 0 4px 20px rgba(15,23,42,0.08) !important;
}}
div[class*="st-key-course_pick_"] button[kind="primary"] {{
  border: 2px solid {PRIMARY_CONTAINER} !important;
  box-shadow: 0 0 0 4px rgba(102,188,176,0.35), 0 8px 28px rgba(0,106,97,0.2) !important;
  font-weight: 600 !important;
}}
div[class*="st-key-course_pick_"] button[kind="secondary"] {{
  background-color: transparent !important; color: #fff !important;
}}

.vx-design-shell {{ margin-top: 1rem; }}
.vx-design-shell .vx-footer-note {{
  text-align: center; font-size: 0.72rem; color: {TEXT_MUTED}; margin-top: 0.65rem;
}}
div[data-testid="stForm"] {{
  background: {GLASS} !important; backdrop-filter: blur(20px) !important;
  border: 1px solid rgba(255,255,255,0.95) !important; border-radius: 999px !important;
  padding: 0.35rem 0.5rem 0.35rem 1rem !important; box-shadow: {SHADOW} !important;
}}
div[data-testid="stForm"] [data-testid="stTextInput"] input {{
  border: none !important; box-shadow: none !important; background: transparent !important;
}}
div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {{
  border-radius: 999px !important; min-width: 11rem;
}}
.tip-glass {{
  background: {LAVENDER} !important; border-radius: 16px !important;
  border: 1px solid rgba(96,78,180,0.12) !important;
}}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header() -> None:
    st.markdown(
        f"""
<div class="app-top">
  <span class="brand">Voyage<span>AI</span> · 강원</span>
  <span class="tag">ETHEREAL INTELLIGENCE</span>
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
  <span class="screen-step {s1}">① Discover</span>
  <span class="screen-step-line {line}"></span>
  <span class="screen-step {s2}">② Your Route</span>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_home_search_hero() -> None:
    st.markdown(
        f"""
<div class="vx-chat-shell">
  <h2>여행의 꿈을 들려주세요</h2>
  <p>{html.escape(get_region_intro())}</p>
  <p class="vx-chat-hint">자연어로 입력하면 AI가 맞춤 코스·지도를 제안합니다</p>
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
        f"linear-gradient(135deg,{PRIMARY_DARK},{PRIMARY})",
        "linear-gradient(135deg,#38bdf8,#7dd3fc)",
        "linear-gradient(135deg,#a78bfa,#ddd6fe)",
        "linear-gradient(135deg,#fb923c,#fed7aa)",
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
    tip_text = (
        '<span style="font-style:italic;color:#5b21b6;">'
        '"The best time to drive the coastal road is just before sunset for that golden hour glow."</span>'
    )

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
  <div class="box tip-glass">
    <p class="lbl">Pro Tip</p>
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


def render_my_trip_hero(meta: dict, step_count: int, query: str) -> None:
    title = html.escape(meta.get("title") or "오늘의 강원도 코스")
    summary = html.escape(meta.get("summary") or "")
    duration = meta.get("total_duration", "")
    dur_chip = f'<span class="mt-chip accent-sky">⏱ {html.escape(duration)}</span>' if duration else ""
    stops_chip = f'<span class="mt-chip accent-lav">{step_count} stops</span>' if step_count else ""
    q = html.escape((query[:56] + "…") if len(query) > 56 else query)
    st.markdown(
        f"""
<div class="mt-hero">
  <div class="mt-hero-row">
    <span class="mt-kicker">YOUR ROUTE</span>
    <span style="display:flex;gap:0.35rem;flex-wrap:wrap;">{stops_chip}{dur_chip}</span>
  </div>
  <h1>{title}</h1>
  <p class="mt-hero-summary">{summary}</p>
  <p class="mt-query">검색 · {q}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def _pill_step_label(step: dict) -> str:
    order = int(step["order"])
    stay = step.get("stay_minutes")
    stay_txt = f" · {stay}분" if stay else ""
    theme = step.get("theme", "여행")
    return f"{order:02d} · {step['spot_name']}\n{step.get('region', '')} · {theme}{stay_txt}"


def _normalize_pill_selection(sel: Any, fallback: int) -> int:
    if sel is None:
        return fallback
    if isinstance(sel, list):
        return int(sel[0]) if sel else fallback
    return int(sel)


def render_route_picker(steps: list[dict]) -> int:
    """일정 박스 = Streamlit pills (CSS 해킹·숨김 버튼 없음)."""
    orders = [int(s["order"]) for s in steps]
    if not orders:
        return 1
    by_order = {int(s["order"]): s for s in steps}
    focus = int(st.session_state.get("focus_order") or orders[0])
    if focus not in orders:
        focus = orders[0]

    st.markdown('<div class="mytrip-route-block">', unsafe_allow_html=True)
    if hasattr(st, "pills"):
        picked = st.pills(
            "일정",
            options=orders,
            format_func=lambda o: _pill_step_label(by_order[o]),
            selection_mode="single",
            default=focus,
            key="mytrip_route_pills",
            label_visibility="collapsed",
        )
    else:
        picked = st.selectbox(
            "일정",
            options=orders,
            index=orders.index(focus),
            format_func=lambda o: _pill_step_label(by_order[o]),
            key="mytrip_route_select",
            label_visibility="collapsed",
        )
    st.markdown("</div>", unsafe_allow_html=True)
    return _normalize_pill_selection(picked, focus)


def render_route_detail_panel(step: dict, spot: dict) -> None:
    """선택한 일정 상세."""
    order = int(step["order"])
    stay = step.get("stay_minutes")
    stay_txt = f" · 약 {stay}분" if stay else ""
    theme = html.escape(step.get("theme", spot.get("theme", "")) or "여행")
    why = html.escape((step.get("why") or spot.get("description") or "").strip())
    move = html.escape((step.get("move_to_next") or "").strip())
    move_html = f'<p class="mt-detail-move">→ {move}</p>' if move else ""
    st.markdown(
        f"""
<div class="mt-detail">
  <div class="mt-detail-top">
    <span class="mt-step-badge">STEP {order:02d}</span>
    <span class="mt-theme-chip">{theme}</span>
  </div>
  <h2>{html.escape(step['spot_name'])}</h2>
  <p class="mt-detail-meta">{html.escape(step.get('region', spot.get('region', '')))}{html.escape(stay_txt)}</p>
  <div class="vx-ai-why">
    <div class="vx-ai-why-label">AI Why</div>
    <p>{why}</p>
  </div>
  {move_html}
</div>
        """,
        unsafe_allow_html=True,
    )
    if spot.get("name") and spot.get("lat") is not None and spot.get("lng") is not None:
        name_q = quote(str(spot["name"]))
        url = f"https://map.kakao.com/link/map/{name_q},{spot['lat']},{spot['lng']}"
        st.link_button("카카오맵에서 열기", url, use_container_width=True)


def _render_theme_tags(steps: list[dict]) -> None:
    themes = sorted({s.get("theme", "") for s in steps if s.get("theme")})
    if not themes:
        return
    tags = "".join(f'<span class="vx-theme-tag">{html.escape(t)}</span>' for t in themes)
    st.markdown(f'<div class="vx-theme-tags">{tags}</div>', unsafe_allow_html=True)


def render_my_trip_route_column(
    steps: list[dict],
    curated: list[dict],
    meta: dict,
) -> tuple[int, dict | None, dict | None]:
    """MY TRIP 왼쪽: 추천 리스트 + AI Why."""
    st.markdown('<p class="vx-split-label">Curated for you</p>', unsafe_allow_html=True)
    _render_theme_tags(steps)
    st.markdown('<p class="mt-panel-label">Timeline</p>', unsafe_allow_html=True)

    picked = render_route_picker(steps)
    st.session_state.focus_order = picked

    focus_step = next((s for s in steps if int(s["order"]) == picked), steps[0] if steps else None)
    focus_db = None
    if focus_step:
        focus_db = next((s for s in curated if s["name"] == focus_step["spot_name"]), curated[0] if curated else None)
        st.markdown('<p class="mt-panel-label">Spot detail</p>', unsafe_allow_html=True)
        render_route_detail_panel(focus_step, focus_db or {})

    trip_text = meta.get("message") or meta.get("summary") or get_region_intro()
    if meta.get("map_tip"):
        trip_text += f"\n\n{meta['map_tip']}"
    with st.expander("코스 전체 보기", expanded=False):
        render_trip_information(trip_text[:1200])

    return picked, focus_step, focus_db


def render_my_trip_map_shell(focus_label: str) -> None:
    st.markdown(
        f"""
<div class="mt-map-card">
  <div class="mt-map-head">
    <h3>Live Map</h3>
    <span>{html.escape(focus_label) if focus_label else "Select a stop"}</span>
  </div>
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


THEME_BADGE = {
    "트레킹": "NATURE",
    "힐링": "CALM",
    "체험": "EXPERIENCE",
    "야경": "NIGHT",
    "역사": "CULTURE",
    "자전거": "DRIVE",
}

THEME_IMAGE = {
    "트레킹": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&h=320&fit=crop&q=80",
    "힐링": "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=600&h=320&fit=crop&q=80",
    "체험": "https://images.unsplash.com/photo-1520250497591-112f2f996a74?w=600&h=320&fit=crop&q=80",
    "야경": "https://images.unsplash.com/photo-1514565131-fce0801e5785?w=600&h=320&fit=crop&q=80",
    "역사": "https://images.unsplash.com/photo-1590736969955-71cc94901144?w=600&h=320&fit=crop&q=80",
    "자전거": "https://images.unsplash.com/photo-1541625602330-2277a4fbfad2?w=600&h=320&fit=crop&q=80",
}
DEFAULT_IMAGE = "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=600&h=320&fit=crop&q=80"


def render_voyage_top_nav(active: str = "explore") -> None:
    tabs = [
        ("explore", "Explore"),
        ("planner", "Planner"),
        ("trips", "My Trips"),
        ("community", "Community"),
    ]
    links = "".join(
        f'<span class="{"on" if key == active else ""}">{label}</span>' for key, label in tabs
    )
    st.markdown(
        f"""
<div class="vx-topnav">
  <div class="vx-topnav-grid">
    <span class="logo">VoyageAI</span>
    <div class="nav-links">{links}</div>
    <div class="nav-right">🔔 ⚙ <span style="width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,{PRIMARY_CONTAINER},{SKY});display:inline-block;vertical-align:middle;"></span></div>
  </div>
  <div class="vx-nav-search">Search destinations…</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_voyage_app_sidebar(active: str = "itinerary") -> None:
    items = [
        ("dashboard", "▦ Dashboard"),
        ("destinations", "◎ Destinations"),
        ("itinerary", "▤ Itinerary"),
        ("favorites", "♡ Favorites"),
    ]
    rows = "".join(
        f'<div class="sb-item {"on" if k == active else ""}">{label}</div>' for k, label in items
    )
    st.markdown(
        f'<div class="vx-sidebar"><div class="sb-logo">VoyageAI</div>{rows}<div class="sb-foot">↪ Logout</div></div>',
        unsafe_allow_html=True,
    )


def render_voyage_profile_sidebar() -> None:
    st.markdown(
        f"""
<div class="vx-profile">
  <div class="avatar"></div>
  <p class="elite">ELITE EXPLORER ✓</p>
  <h4>Alex Jung</h4>
  <div class="vx-stat-row">
    <div class="vx-stat"><strong>12</strong><span>Trips</span></div>
    <div class="vx-stat"><strong>840</strong><span>Points</span></div>
  </div>
  <p style="margin:0.85rem 0 0.4rem;font-size:11px;font-weight:700;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.05em;">Interests ✎</p>
  <div class="vx-theme-tags">
    <span class="vx-theme-tag" style="background:{PRIMARY_CONTAINER};color:{T.on_primary_container};">Coastal Drive</span>
    <span class="vx-theme-tag" style="background:{SKY};color:{T.on_secondary_container};">Gastronomy</span>
    <span class="vx-theme-tag" style="background:{LAVENDER};color:{T.on_tertiary_container};">Photography</span>
    <span class="vx-theme-tag">+3 More</span>
  </div>
  <div style="margin-top:1rem;padding:0.75rem;background:{T.surface_container_low};border-radius:16px;border:1px solid {T.outline_variant};">
    <p style="margin:0 0 0.35rem;font-size:11px;font-weight:700;color:{TEXT_MUTED};text-transform:uppercase;">Saved Discovery ♡</p>
    <p style="margin:0;font-size:0.8rem;font-weight:700;color:{TEXT};">East Coast Scenic Route</p>
    <p style="margin:0.25rem 0 0;font-size:0.72rem;color:{TEXT_MUTED};">Saved on Sep 14 · 4.2 mi</p>
  </div>
  <div style="margin-top:0.65rem;padding:0.75rem;background:{LAVENDER};border-radius:16px;">
    <p style="margin:0;font-size:0.78rem;color:{T.on_tertiary_container};">🎁 <strong>Travel Voucher</strong><br/>15% off car rentals in Gangwon</p>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_welcome_banner() -> None:
    st.markdown(
        f"""
<div class="vx-welcome">
  <h2>HELLO, TRAVELER</h2>
  <p>{html.escape(get_region_intro())}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_home_chat_section(last_query: str = "") -> None:
    ai_msg = (
        "Based on your interest in photography and coastal views, I recommend "
        "starting at Nami Island and moving toward the East Sea coast."
    )
    user_msg = last_query or (
        "That sounds perfect. Can we include a stop at a famous local coffee shop too?"
    )
    st.markdown(
        f"""
<div class="vx-chat-box">
  <div class="vx-bubble-ai">✦ {html.escape(ai_msg)}</div>
  <div class="vx-bubble-user">{html.escape(user_msg)}</div>
  <div class="vx-quick-pills">
    <span>Coffee Shops in Gangneung</span><span>Sunset Spots</span><span>Parking Info</span>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _planner_course_pill_label(step: dict, spot: dict) -> str:
    theme = step.get("theme") or spot.get("theme") or "힐링"
    badge = THEME_BADGE.get(theme, "SPOT")
    name = step["spot_name"]
    region = step.get("region") or spot.get("region") or ""
    stay = step.get("stay_minutes")
    price = f"약 {stay}분" if stay else "추천 코스"
    why = (step.get("why") or spot.get("description") or "").strip()
    if len(why) > 88:
        why = why[:85] + "…"
    return f"{badge}  ·  {price}\n{name}\n📍 {region}\n✦ {why}"


def _inject_planner_course_button_styles(steps: list[dict]) -> None:
    """일정별 히어로 이미지 — st-key-course_pick_N 버튼에 적용."""
    rules: list[str] = []
    for step in steps:
        order = int(step["order"])
        theme = step.get("theme") or "힐링"
        img = THEME_IMAGE.get(theme, DEFAULT_IMAGE)
        bg = (
            f"linear-gradient(180deg, rgba(255,255,255,0.05) 0%, "
            f"rgba(23,29,28,0.82) 100%), url(\"{img}\")"
        )
        rules.append(
            f"""
div.st-key-course_pick_{order} button {{
  background: {bg} center/cover no-repeat !important;
  color: #fff !important;
}}
"""
        )
    if rules:
        st.markdown(f"<style>{''.join(rules)}</style>", unsafe_allow_html=True)


def render_tailored_header(meta: dict, query: str, step_count: int) -> None:
    title = html.escape(meta.get("title") or "Tailored for You")
    summary = html.escape(
        meta.get("summary")
        or "Based on your preferences for nature, calm landscapes, and scenic drives in Gangwon province."
    )
    duration = html.escape(meta.get("total_duration") or "당일 코스")
    q = html.escape((query[:48] + "…") if len(query) > 48 else query)
    st.markdown(
        f"""
<div class="vx-tailored-head">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;">
    <div>
      <h1>{title}</h1>
      <p>{summary}</p>
      <p style="margin-top:0.35rem;font-size:0.78rem;color:{TEXT_MUTED};">검색 · {q}</p>
    </div>
    <div class="vx-head-chips">
      <span class="vx-head-chip">✓ AI OPTIMIZED</span>
      <span class="vx-head-chip">⏱ {duration}</span>
      <span class="vx-head-chip">{step_count} stops</span>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_course_cards_list(
    steps: list[dict],
    curated: list[dict],
    focus_order: int,
) -> int:
    """Daily Course — 카드 전체가 클릭 가능한 wide button (「이 코스 보기」 없음)."""
    orders = [int(s["order"]) for s in steps]
    if not orders:
        return int(focus_order or 1)

    spot_by = {s["name"]: s for s in curated}
    focus = int(focus_order or orders[0])
    if focus not in orders:
        focus = orders[0]

    st.markdown(
        '<p class="mt-panel-label" style="margin-top:0;">Daily Courses</p>',
        unsafe_allow_html=True,
    )
    _inject_planner_course_button_styles(steps)

    picked = focus
    for step in steps:
        order = int(step["order"])
        spot = spot_by.get(step["spot_name"], {})
        label = _planner_course_pill_label(step, spot)
        if st.button(
            label,
            key=f"course_pick_{order}",
            type="primary" if order == focus else "secondary",
            use_container_width=True,
        ):
            picked = order

    if picked != focus:
        st.session_state.focus_order = picked
        st.rerun()

    st.session_state.focus_order = picked
    return int(picked)


def render_voyage_explore_page(spot_count: int) -> None:
    """홈 — Explore 시안 (Stitch 1.md)."""
    render_voyage_top_nav("explore")
    main_col, side_col = st.columns([2.35, 1], gap="medium")
    with main_col:
        render_welcome_banner()
        render_gangwon_dashboard()
        render_home_chat_section(st.session_state.get("last_user_query", ""))
        st.markdown(
            f'<div class="vx-design-shell"><p class="vx-footer-note">'
            f"Currently indexing {spot_count} major tourist destinations in Gangwon region without filters."
            f"</p></div>",
            unsafe_allow_html=True,
        )
    with side_col:
        render_voyage_profile_sidebar()


def map_card_open(title: str) -> None:
    st.markdown(f'<div class="map-shell"><div class="map-label">{html.escape(title)}</div>', unsafe_allow_html=True)


def map_card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
