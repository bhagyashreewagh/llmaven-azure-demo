"""LLM Spend Intelligence - Interactive Analytics Dashboard
University of Washington, eScience Institute, Jan-Mar 2026
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import zipfile, json, os, re
import numpy as np
from pathlib import Path
import anthropic

# Load API key from Kyron Medical .env if not already in environment
_env_path = Path("/Users/a91885/Desktop/Kyron Medical/.env")
if not os.getenv("ANTHROPIC_API_KEY") and _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        if _line.startswith("ANTHROPIC_API_KEY="):
            os.environ["ANTHROPIC_API_KEY"] = _line.split("=", 1)[1].strip()
            break

st.set_page_config(
    page_title="LLM Spend Intelligence",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

ZIP_PATH = Path(os.getenv("DATA_ZIP", "/Users/a91885/Downloads/jan-feb-march-2026.zip"))

# Skydash-inspired: violet-blue, sail blue, tonys pink on white
C = {
    "bg":         "#F4F7FF",
    "card":       "#FFFFFF",
    "sidebar":    "#1B2942",
    "primary":    "#6571FF",
    "primary_dk": "#4D59E8",
    "sail":       "#7DA0FA",
    "sail_lt":    "#B8CCFF",
    "pink":       "#FC84A9",
    "pink_lt":    "#FDB8CD",
    "text":       "#2B2B2B",
    "text_md":    "#4A4A68",
    "muted":      "#7987A1",
    "border":     "#E8EEFF",
    "success":    "#00C9A7",
    "danger":     "#FC5A5A",
}

SEQ = [
    "#6571FF", "#FC84A9", "#7DA0FA", "#4D59E8",
    "#FDB8CD", "#B8CCFF", "#3848D0", "#F97FAB",
    "#5A8CF8", "#9BA6FF",
]

_PL = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#FFFFFF",
    font=dict(color="#2B2B2B", family="Poppins, sans-serif", size=14),
    margin=dict(t=45, b=30, l=10, r=10),
    hoverlabel=dict(bgcolor="#6571FF", font_color="white", font_size=14),
    uniformtext=dict(minsize=9, mode="hide"),
)

# Inline SVG illustrations
SVG_ANALYTICS = """<svg width="300" height="160" viewBox="0 0 300 160" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="cs"><feDropShadow dx="0" dy="4" stdDeviation="8" flood-color="rgba(101,113,255,0.15)"/></filter>
  </defs>
  <rect x="8" y="12" width="170" height="108" rx="14" fill="white" filter="url(#cs)"/>
  <rect x="8" y="12" width="170" height="6" rx="4" fill="#6571FF"/>
  <rect x="22" y="28" width="55" height="6" rx="3" fill="#B8CCFF"/>
  <rect x="22" y="40" width="36" height="4" rx="2" fill="#E8EEFF"/>
  <rect x="22" y="82" width="13" height="24" rx="3" fill="#B8CCFF"/>
  <rect x="39" y="70" width="13" height="36" rx="3" fill="#7DA0FA"/>
  <rect x="56" y="58" width="13" height="48" rx="3" fill="#6571FF"/>
  <rect x="73" y="72" width="13" height="34" rx="3" fill="#7DA0FA"/>
  <rect x="90" y="50" width="13" height="56" rx="3" fill="#4D59E8"/>
  <rect x="107" y="60" width="13" height="46" rx="3" fill="#6571FF"/>
  <rect x="124" y="55" width="13" height="51" rx="3" fill="#4D59E8"/>
  <rect x="141" y="63" width="13" height="43" rx="3" fill="#7DA0FA"/>
  <polyline points="28,78 45,66 62,54 79,68 96,46 113,57 130,51 147,58"
            stroke="#FC84A9" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="62" cy="54" r="4" fill="#FC84A9"/>
  <circle cx="96" cy="46" r="4" fill="#FC84A9"/>
  <circle cx="130" cy="51" r="4" fill="#FC84A9"/>
  <rect x="190" y="8" width="102" height="60" rx="12" fill="white" filter="url(#cs)"/>
  <rect x="202" y="22" width="40" height="5" rx="2" fill="#B8CCFF"/>
  <rect x="202" y="33" width="75" height="10" rx="3" fill="rgba(101,113,255,0.08)"/>
  <rect x="202" y="33" width="50" height="10" rx="3" fill="rgba(101,113,255,0.35)"/>
  <rect x="254" y="21" width="28" height="8" rx="4" fill="rgba(252,132,169,0.2)"/>
  <rect x="258" y="24" width="16" height="3" rx="1" fill="#FC84A9"/>
  <rect x="190" y="82" width="102" height="58" rx="12" fill="white" filter="url(#cs)"/>
  <rect x="202" y="92" width="36" height="5" rx="2" fill="#B8CCFF"/>
  <polyline points="202,118 216,107 230,112 244,102 258,105 278,93"
            stroke="#6571FF" stroke-width="2" fill="none" stroke-linecap="round"/>
  <circle cx="278" cy="93" r="4" fill="#6571FF"/>
  <circle cx="178" cy="142" r="6" fill="#FC84A9" opacity="0.25"/>
  <circle cx="188" cy="130" r="4" fill="#6571FF" opacity="0.2"/>
  <circle cx="288" cy="148" r="8" fill="#7DA0FA" opacity="0.18"/>
</svg>"""

SVG_AI_BOT = """<svg width="200" height="195" viewBox="0 0 200 195" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="bs"><feDropShadow dx="0" dy="6" stdDeviation="10" flood-color="rgba(101,113,255,0.25)"/></filter>
  </defs>
  <rect x="52" y="92" width="82" height="72" rx="16" fill="#6571FF" filter="url(#bs)"/>
  <rect x="84" y="85" width="18" height="12" rx="4" fill="#5562E8"/>
  <rect x="57" y="35" width="72" height="55" rx="16" fill="#7DA0FA" filter="url(#bs)"/>
  <rect x="95" y="18" width="6" height="20" rx="3" fill="#7987A1"/>
  <circle cx="98" cy="14" r="8" fill="#FC84A9"/>
  <circle cx="98" cy="14" r="4" fill="white" opacity="0.5"/>
  <rect x="71" y="48" width="19" height="16" rx="7" fill="white"/>
  <rect x="96" y="48" width="19" height="16" rx="7" fill="white"/>
  <circle cx="80" cy="56" r="5" fill="#6571FF"/>
  <circle cx="105" cy="56" r="5" fill="#6571FF"/>
  <circle cx="82" cy="54" r="2" fill="white"/>
  <circle cx="107" cy="54" r="2" fill="white"/>
  <rect x="76" y="74" width="34" height="8" rx="4" fill="rgba(255,255,255,0.3)"/>
  <rect x="80" y="76" width="22" height="4" rx="2" fill="rgba(255,255,255,0.55)"/>
  <rect x="18" y="97" width="36" height="18" rx="9" fill="#7DA0FA"/>
  <rect x="132" y="97" width="36" height="18" rx="9" fill="#7DA0FA"/>
  <rect x="67" y="108" width="52" height="36" rx="10" fill="rgba(255,255,255,0.15)"/>
  <circle cx="82" cy="126" r="6" fill="#FC84A9" opacity="0.9"/>
  <circle cx="98" cy="126" r="6" fill="rgba(255,255,255,0.65)"/>
  <circle cx="114" cy="126" r="6" fill="#B8CCFF"/>
  <rect x="67" y="160" width="22" height="28" rx="10" fill="#7DA0FA"/>
  <rect x="97" y="160" width="22" height="28" rx="10" fill="#7DA0FA"/>
  <rect x="130" y="18" width="62" height="46" rx="11" fill="white" filter="url(#bs)"/>
  <polygon points="134,46 144,58 154,46" fill="white"/>
  <circle cx="148" cy="41" r="5" fill="#6571FF"/>
  <circle cx="162" cy="41" r="5" fill="#FC84A9"/>
  <circle cx="176" cy="41" r="5" fill="#7DA0FA"/>
  <rect x="140" y="26" width="44" height="5" rx="2" fill="#E8EEFF"/>
  <rect x="140" y="34" width="30" height="5" rx="2" fill="#E8EEFF"/>
  <path d="M30 40 L32 33 L34 40 L41 42 L34 44 L32 51 L30 44 L23 42Z" fill="#FC84A9" opacity="0.45"/>
  <path d="M185 148 L186 143 L187 148 L192 149 L187 150 L186 155 L185 150 L180 149Z" fill="#6571FF" opacity="0.4"/>
  <circle cx="35" cy="155" r="8" fill="#B8CCFF" opacity="0.3"/>
</svg>"""

SVG_CACHE = """<svg width="170" height="155" viewBox="0 0 170 155" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="glow"><feDropShadow dx="0" dy="4" stdDeviation="12" flood-color="rgba(101,113,255,0.3)"/></filter>
  </defs>
  <circle cx="85" cy="78" r="68" fill="rgba(101,113,255,0.05)" stroke="#B8CCFF" stroke-width="1.5" stroke-dasharray="6,4"/>
  <circle cx="85" cy="78" r="50" fill="rgba(101,113,255,0.08)" stroke="#7DA0FA" stroke-width="1.5"/>
  <circle cx="85" cy="78" r="34" fill="#6571FF" filter="url(#glow)"/>
  <path d="M91 50 L75 80 L86 80 L79 106 L99 70 L87 70 Z" fill="white"/>
  <circle cx="85" cy="10" r="6" fill="#FC84A9"/>
  <circle cx="147" cy="50" r="5" fill="#7DA0FA"/>
  <circle cx="147" cy="106" r="5" fill="#7DA0FA"/>
  <circle cx="85" cy="146" r="6" fill="#FC84A9"/>
  <circle cx="23" cy="106" r="5" fill="#B8CCFF"/>
  <circle cx="23" cy="50" r="5" fill="#B8CCFF"/>
</svg>"""

# CSS
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

  * {{ font-family: 'Poppins', sans-serif !important; font-size: 15px; }}
  .stApp {{ background-color: {C['bg']}; }}
  .main .block-container {{ padding-top: 1.4rem; max-width: 1440px; }}
  #MainMenu,
  footer,
  header,
  [data-testid="stHeader"],
  [data-testid="stToolbar"],
  [data-testid="stDecoration"],
  [data-testid="stStatusWidget"],
  [data-testid="stDeployButton"],
  [data-testid="stSidebarCollapseButton"],
  [data-testid="stMainBlockContainer"] > div:first-child > div:first-child > div:first-child button[kind="header"]
  {{ display: none !important; }}

  /* Full-page branded loading screen */
  [data-testid="stSpinner"] {{
    position: fixed !important;
    inset: 0 !important;
    background: linear-gradient(145deg, {C['sidebar']} 0%, #2A3BAA 55%, {C['primary']} 100%) !important;
    z-index: 99999 !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0 !important;
  }}
  [data-testid="stSpinner"]::before {{
    content: 'LLM Spend Intelligence';
    display: block;
    color: white;
    font-size: 2.4rem;
    font-weight: 800;
    font-family: 'Poppins', -apple-system, sans-serif;
    letter-spacing: -0.02em;
    margin-bottom: 0.4rem;
  }}
  [data-testid="stSpinner"]::after {{
    content: 'University of Washington · eScience Institute';
    display: block;
    color: rgba(255,255,255,0.5);
    font-size: 0.85rem;
    font-family: 'Poppins', -apple-system, sans-serif;
    font-weight: 400;
    letter-spacing: 0.04em;
    margin-bottom: 3rem;
  }}
  [data-testid="stSpinner"] > div {{
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    gap: 1rem !important;
  }}
  [data-testid="stSpinner"] p,
  [data-testid="stSpinner"] span {{
    color: rgba(255,255,255,0.6) !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    font-family: 'Poppins', -apple-system, sans-serif !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
  }}
  [data-testid="stSpinner"] svg {{
    width: 48px !important;
    height: 48px !important;
    color: white !important;
  }}
  [data-testid="stSpinner"] svg circle {{
    stroke: rgba(255,255,255,0.25) !important;
  }}
  [data-testid="stSpinner"] svg path,
  [data-testid="stSpinner"] svg line {{
    stroke: white !important;
  }}

  [data-testid="stSidebar"] {{
    background-color: {C['sidebar']} !important;
    min-width: 310px !important;
    max-width: 310px !important;
    transform: translateX(0) !important;
    visibility: visible !important;
  }}
  [data-testid="stSidebar"] > div:first-child {{ background-color: {C['sidebar']}; }}

  /* Sidebar toggle button - make it visible and on-brand */
  [data-testid="collapsedControl"] {{
    background: {C['primary']} !important;
    border-radius: 0 10px 10px 0 !important;
    height: 56px !important;
    width: 28px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 3px 0 14px rgba(101,113,255,0.35) !important;
    top: calc(50% - 28px) !important;
    position: fixed !important;
    left: 0 !important;
  }}
  [data-testid="collapsedControl"] svg {{
    color: white !important;
    width: 18px !important;
    height: 18px !important;
  }}
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] .stMarkdown {{ color: rgba(255,255,255,0.72) !important; }}
  [data-testid="stSidebar"] label {{
    color: rgba(255,255,255,0.55) !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600 !important;
  }}
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 {{ color: white !important; }}
  [data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.1); }}
  [data-testid="stSidebar"] .stButton button {{
    background: rgba(101,113,255,0.3) !important;
    color: white !important;
    border: 1px solid rgba(101,113,255,0.4) !important;
    border-radius: 10px !important;
    width: 100%;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
  }}

  .stTabs [data-baseweb="tab-list"] {{
    background: {C['card']};
    border-radius: 14px;
    padding: 5px;
    gap: 3px;
    box-shadow: 0 2px 14px rgba(101,113,255,0.08);
  }}
  .stTabs [data-baseweb="tab"] {{
    border-radius: 10px;
    padding: 9px 22px;
    font-weight: 600;
    font-size: 1.25rem;
    color: {C['muted']};
    background: transparent;
    border: none;
  }}
  .stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg, {C['primary']}, {C['primary_dk']}) !important;
    color: white !important;
    box-shadow: 0 4px 14px rgba(101,113,255,0.35);
  }}

  .kpi {{
    background: {C['card']};
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    box-shadow: 0 4px 20px rgba(101,113,255,0.07);
    border: 1px solid {C['border']};
    position: relative;
    overflow: hidden;
    height: 158px;
    box-sizing: border-box;
  }}
  .kpi::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
    background: linear-gradient(90deg, {C['primary']}, {C['pink']});
  }}
  .kpi-val {{
    font-size: 2.1rem;
    font-weight: 800;
    color: {C['primary']};
    line-height: 1.1;
    margin-bottom: 0.15rem;
  }}
  .kpi-lbl {{
    font-size: 0.8rem;
    color: {C['muted']};
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 0.3rem;
    font-weight: 600;
  }}
  .kpi-note {{ font-size: 0.9rem; color: {C['muted']}; margin-top: 0.25rem; }}
  .kpi-note.warn {{ color: {C['danger']}; }}
  .kpi-note.good {{ color: {C['success']}; }}

  .insight {{
    background: linear-gradient(135deg, rgba(101,113,255,0.06), rgba(252,132,169,0.06));
    border-radius: 12px;
    padding: 0.95rem 1.2rem;
    border-left: 3px solid {C['primary']};
    font-size: 1rem;
    color: {C['text_md']};
    margin-top: 0.6rem;
    line-height: 1.65;
  }}
  .insight b {{ color: {C['primary_dk']}; }}

  .sec {{
    font-size: 1.15rem;
    font-weight: 700;
    color: {C['text']};
    border-bottom: 2px solid {C['border']};
    padding-bottom: 0.4rem;
    margin-bottom: 0.8rem;
    margin-top: 0.2rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }}
  .sec-dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
    background: linear-gradient(135deg, {C['primary']}, {C['pink']});
    display: inline-block;
    flex-shrink: 0;
  }}

  .div {{
    height: 1px;
    background: linear-gradient(90deg, {C['primary']}, {C['pink']}, transparent);
    margin: 1rem 0;
    opacity: 0.25;
  }}

  .lr {{ border-top: 1px solid {C['border']}; margin: 0.15rem 0; }}

  .rank {{
    font-size: 1rem;
    font-weight: 800;
    padding: 0.35rem 0.65rem;
    background: rgba(101,113,255,0.08);
    border-radius: 8px;
    display: inline-block;
    min-width: 38px;
    text-align: center;
    color: {C['primary']};
  }}
  .rank.gold   {{ color: #D4A017; background: rgba(212,160,23,0.12); }}
  .rank.silver {{ color: #8B9BB4; background: rgba(139,155,180,0.12); }}
  .rank.bronze {{ color: #CD7F32; background: rgba(205,127,50,0.12); }}

  .savings-banner {{
    background: linear-gradient(135deg, {C['primary_dk']}, {C['primary']}, {C['sail']});
    border-radius: 18px;
    padding: 2rem 2.4rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
  }}
  .savings-banner::after {{
    content: '';
    position: absolute;
    top: -50px; right: -50px;
    width: 220px; height: 220px;
    border-radius: 50%;
    background: rgba(255,255,255,0.05);
  }}
  .savings-big {{
    color: white;
    font-size: 2.9rem;
    font-weight: 900;
    line-height: 1.1;
  }}
  .savings-lbl {{
    color: rgba(255,255,255,0.65);
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.25rem;
    font-weight: 600;
  }}
  .savings-note {{ color: {C['pink_lt']}; font-size: 0.95rem; margin-top: 0.3rem; }}

  .ai-header {{
    background: {C['card']};
    border-radius: 16px;
    padding: 1.6rem 2rem;
    border: 1px solid {C['border']};
    margin-bottom: 1.4rem;
    box-shadow: 0 2px 12px rgba(101,113,255,0.06);
  }}
  .ai-answer {{
    background: {C['card']};
    border-radius: 16px;
    padding: 1.6rem 1.8rem;
    border-left: 4px solid {C['primary']};
    box-shadow: 0 4px 20px rgba(101,113,255,0.1);
    margin-top: 1.2rem;
    font-size: 1.05rem;
    line-height: 1.75;
    color: {C['text']};
  }}
  .ai-lbl {{
    font-size: 0.8rem;
    color: {C['muted']};
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 700;
    margin-bottom: 0.8rem;
  }}

  .stButton button {{
    background: {C['card']};
    color: {C['primary']};
    border: 1.5px solid {C['border']};
    border-radius: 20px;
    font-size: 0.9rem;
    font-weight: 600;
    transition: all 0.15s ease;
  }}
  .stButton button:hover {{
    background: {C['primary']};
    color: white;
    border-color: {C['primary']};
    box-shadow: 0 4px 12px rgba(101,113,255,0.3);
  }}

  .stTextInput input {{
    border-radius: 12px !important;
    border: 1.5px solid {C['border']} !important;
    font-size: 0.95rem !important;
    padding: 0.7rem 1rem !important;
  }}
  .stTextInput input:focus {{
    border-color: {C['primary']} !important;
    box-shadow: 0 0 0 3px rgba(101,113,255,0.12) !important;
  }}

  ::-webkit-scrollbar {{ width: 6px; }}
  ::-webkit-scrollbar-track {{ background: {C['bg']}; }}
  ::-webkit-scrollbar-thumb {{ background: {C['sail_lt']}; border-radius: 3px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: {C['sail']}; }}
</style>
""", unsafe_allow_html=True)


def fmt_usd(v: float) -> str:
    return f"${v:,.4f}" if v < 1 else f"${v:,.2f}"

def fmt_k(v: float) -> str:
    if v >= 1_000_000: return f"{v/1e6:.2f}M"
    if v >= 1_000:     return f"{v/1e3:.1f}K"
    return f"{int(v):,}"

def kpi(label: str, value: str, note: str = "", note_cls: str = "") -> str:
    note_html = f"<div class='kpi-note {note_cls}'>{note}</div>" if note else ""
    return (
        f"<div class='kpi'>"
        f"<div class='kpi-lbl'>{label}</div>"
        f"<div class='kpi-val'>{value}</div>"
        f"{note_html}</div>"
    )

def insight(text: str) -> str:
    return f"<div class='insight'>{text}</div>"

def sec(text: str) -> str:
    return f"<div class='sec'><span class='sec-dot'></span>{text}</div>"

def md_to_html(text: str) -> str:
    return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

def _style(fig, height: int = None, legend: str = None, margin_b: int = None):
    """Apply consistent axis colours and optional legend/height to any Plotly figure."""
    if height:
        fig.update_layout(height=height)
    if margin_b is not None:
        fig.update_layout(margin=dict(t=45, b=margin_b, l=10, r=10))
    if legend == "below":
        fig.update_layout(margin=dict(t=45, b=80, l=10, r=10))
        fig.update_layout(legend=dict(
            orientation="h", y=-0.28, x=0.5, xanchor="center",
            font=dict(size=14, color=C["text"]), bgcolor="rgba(0,0,0,0)",
        ))
    elif legend == "none":
        fig.update_layout(showlegend=False)
    # Always enforce visible axis colours
    fig.update_xaxes(
        title_font=dict(size=15, color=C["muted"]),
        tickfont=dict(size=13, color=C["text_md"]),
        zeroline=False,
    )
    fig.update_yaxes(
        title_font=dict(size=15, color=C["muted"]),
        tickfont=dict(size=13, color=C["text_md"]),
        zeroline=False,
        rangemode="tozero",
    )
    return fig


def _clean_model(raw: str) -> str:
    r = raw.lower()
    if "haiku"  in r:                    return "Claude Haiku"
    if "sonnet" in r and "bedrock" in r: return "Claude Sonnet (Bedrock)"
    if "sonnet" in r:                    return "Claude Sonnet"
    if "gpt" in r or "openai" in r:      return "OpenAI (GPT)"
    if "opus" in r:                      return "Claude Opus"
    return "Other"

def _cache_savings(row) -> float:
    t = row["cache_read"]
    if t <= 0: return 0.0
    rate = (0.80 - 0.08) if "haiku" in row["model_raw"].lower() else (3.00 - 0.30)
    return t * rate / 1_000_000


@st.cache_data(show_spinner="Parsing 3 months of API call logs...")
def load_data() -> pd.DataFrame:
    rows = []
    with zipfile.ZipFile(ZIP_PATH) as zf:
        for name in sorted(zf.namelist()):
            if not name.endswith(".jsonl"):
                continue
            with zf.open(name) as f:
                for raw_line in f:
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    try:
                        r   = json.loads(raw_line)
                        m   = r.get("metadata") or {}
                        u   = m.get("usage_object") or {}
                        ptd = u.get("prompt_tokens_details") or {}
                        ctd = u.get("completion_tokens_details") or {}
                        rows.append({
                            "request_id":        r.get("request_id", ""),
                            "spend":             float(r.get("spend") or 0),
                            "model_raw":         str(r.get("model") or ""),
                            "status":            r.get("status", "unknown"),
                            "start_time":        r.get("startTime"),
                            "end_time":          r.get("endTime"),
                            "total_tokens":      int(r.get("total_tokens") or 0),
                            "prompt_tokens":     int(r.get("prompt_tokens") or 0),
                            "completion_tokens": int(r.get("completion_tokens") or 0),
                            "session_id":        r.get("session_id", ""),
                            "user":              m.get("user_api_key_alias") or "unknown",
                            "team":              m.get("user_api_key_team_alias") or "No Team",
                            "cache_read":        int(u.get("cache_read_input_tokens")
                                                    or ptd.get("cached_tokens") or 0),
                            "cache_create":      int(u.get("cache_creation_input_tokens")
                                                    or ptd.get("cache_creation_tokens") or 0),
                            "reasoning_tokens":  int(ctd.get("reasoning_tokens") or 0),
                        })
                    except Exception:
                        continue

    df = pd.DataFrame(rows)
    df["start_dt"] = pd.to_datetime(df["start_time"], utc=True, errors="coerce")
    df["end_dt"]   = pd.to_datetime(df["end_time"],   utc=True, errors="coerce")
    df = df.dropna(subset=["start_dt"])
    df["date"]    = df["start_dt"].dt.date
    df["hour"]    = df["start_dt"].dt.hour
    df["dow"]     = df["start_dt"].dt.day_name()
    df["month"]   = df["start_dt"].dt.month_name()
    df["latency"] = (df["end_dt"] - df["start_dt"]).dt.total_seconds().clip(0, 300)
    df["model"]   = df["model_raw"].apply(_clean_model)
    df["cache_savings"] = df.apply(_cache_savings, axis=1)
    HAIKU_IN, HAIKU_OUT = 0.80 / 1_000_000, 4.00 / 1_000_000
    df["spend_haiku"] = df["prompt_tokens"] * HAIKU_IN + df["completion_tokens"] * HAIKU_OUT
    return df


df_all = load_data()

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style='padding:.6rem 0 .3rem'>
      <div style='font-size:1.4rem;font-weight:800;color:white;letter-spacing:-0.02em'>
        LLM Spend
      </div>
      <div style='font-size:0.75rem;color:rgba(255,255,255,0.5);margin-top:0.1rem;font-weight:500'>
        Intelligence Dashboard
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    min_d, max_d = df_all["date"].min(), df_all["date"].max()
    st.markdown(
        "<p style='font-size:0.7rem;color:rgba(255,255,255,0.55);text-transform:uppercase;"
        "letter-spacing:0.1em;font-weight:600;margin-bottom:0.3rem'>Analysis Window</p>",
        unsafe_allow_html=True,
    )
    date_range = st.date_input(
        "Analysis Window",
        value=(min_d, max_d),
        min_value=min_d,
        max_value=max_d,
        label_visibility="collapsed",
        format="MM/DD/YYYY",
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.session_state.pop("_do_reset", False):
        st.session_state["sb_users"]   = []
        st.session_state["sb_models"]  = []
        st.session_state["sb_outcome"] = []
    sel_users    = st.multiselect("Users",          sorted(df_all["user"].unique()),   placeholder="All users",   key="sb_users")
    sel_models   = st.multiselect("Models",         sorted(df_all["model"].unique()),  placeholder="All models",  key="sb_models")
    sel_statuses = st.multiselect("Call Outcome",   sorted(df_all["status"].unique()), placeholder="success + failure", key="sb_outcome")

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("Reset Filters", use_container_width=True):
        st.session_state["_do_reset"] = True
        st.rerun()


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if len(date_range) == 2:
        df = df[(df["date"] >= date_range[0]) & (df["date"] <= date_range[1])]
    if sel_users:    df = df[df["user"].isin(sel_users)]
    if sel_models:   df = df[df["model"].isin(sel_models)]
    if sel_statuses: df = df[df["status"].isin(sel_statuses)]
    return df

df = apply_filters(df_all)

# Page header
hc1, hc2 = st.columns([4, 1])
with hc1:
    if len(df):
        d_from   = df["date"].min().strftime("%B %d, %Y")
        d_to     = df["date"].max().strftime("%B %d, %Y")
        n_days   = (df["date"].max() - df["date"].min()).days + 1
        total_av = (df_all["date"].max() - df_all["date"].min()).days + 1
        is_sub   = len(df) < len(df_all) or n_days < total_av
        sub_note = (
            f"Filtered view &nbsp;|&nbsp; {n_days}-day window: {d_from} to {d_to}"
            if is_sub else
            f"{n_days}-day window: {d_from} to {d_to}"
        )
    else:
        sub_note = "No data matches current filters"
    st.markdown(f"""
    <div style='margin-bottom:0.5rem'>
      <div style='font-size:1.85rem;font-weight:800;color:{C["text"]};letter-spacing:-0.02em'>
        LLM Spend Intelligence
      </div>
      <div style='color:{C["muted"]};font-size:0.88rem;margin-top:0.15rem;font-weight:500'>
        University of Washington, eScience Institute &nbsp;|&nbsp; {sub_note}
      </div>
    </div>
    """, unsafe_allow_html=True)
with hc2:
    if any([sel_users, sel_models, sel_statuses]):
        st.markdown(
            f"<div style='text-align:right;color:{C['primary']};font-size:0.84rem;"
            f"font-weight:700;padding-top:1.1rem'>{len(df):,} / {len(df_all):,} requests</div>",
            unsafe_allow_html=True,
        )

st.markdown('<div class="div"></div>', unsafe_allow_html=True)

t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "Overview",
    "Cost Explorer",
    "Time Intelligence",
    "Users",
    "Cache",
    "Sessions",
    "Ask the Data",
])


# TAB 1 - OVERVIEW
with t1:
    total_spend    = df["spend"].sum()
    total_requests = len(df)
    unique_users   = df["user"].nunique()
    total_tokens   = df["total_tokens"].sum()
    total_savings  = df["cache_savings"].sum()
    failures       = (df["status"] == "failure").sum()

    k1, k2, k3, k4, k5 = st.columns(5)
    fail_pct = failures / total_requests * 100 if total_requests else 0
    k1.markdown(kpi("Total Spend",   fmt_usd(total_spend),  f"across {total_requests:,} API calls"), unsafe_allow_html=True)
    k2.markdown(kpi("API Requests",  f"{total_requests:,}", f"{failures:,} errors &nbsp;({fail_pct:.1f}%)", "warn" if failures > 0 else ""), unsafe_allow_html=True)
    k3.markdown(kpi("Active Users",  str(unique_users),     "distinct API key holders"), unsafe_allow_html=True)
    k4.markdown(kpi("Tokens Used",   fmt_k(total_tokens),   "prompt + completion + cached"), unsafe_allow_html=True)
    k5.markdown(kpi("Cache Savings", fmt_usd(total_savings), "vs. billing all tokens at standard rates", "good"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(sec("Daily Spend Trend"), unsafe_allow_html=True)
    daily = df.groupby("date")["spend"].sum().reset_index()
    daily["date"]   = pd.to_datetime(daily["date"])
    daily["7d_avg"] = daily["spend"].rolling(7, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["date"], y=[0] * len(daily),
        line=dict(width=0), showlegend=False, hoverinfo="skip",
        name="_base",
    ))
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["spend"],
        fill="tonexty", name="Daily Spend ($)",
        line=dict(color=C["primary"], width=2.5),
        fillcolor="rgba(101,113,255,0.12)",
        hovertemplate="<b>%{x|%b %d}</b><br>$%{y:.4f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["7d_avg"],
        name="7-Day Rolling Average",
        line=dict(color=C["pink"], width=2.5, dash="dot"),
        hovertemplate="7-day avg: $%{y:.4f}<extra></extra>",
    ))
    fig.update_layout(
        **_PL, height=310,
        legend=dict(
            orientation="h", y=1.14, x=0,
            font=dict(size=14, color=C["text"]),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor=C["border"], borderwidth=1,
        ),
        xaxis=dict(
            title=dict(text="Date", font=dict(size=13, color=C["muted"])),
            showgrid=False,
            tickformat="%b %d",
            tickfont=dict(size=12, color=C["text_md"]),
        ),
        yaxis=dict(
            title=dict(text="Daily Spend (USD)", font=dict(size=13, color=C["muted"])),
            tickprefix="$",
            gridcolor="#E8EEFF",
            tickfont=dict(size=12, color=C["text_md"]),
        ),
    )
    _style(fig)
    st.plotly_chart(fig, use_container_width=True)

    peak = daily.loc[daily["spend"].idxmax()]
    avg  = daily["spend"].mean()
    st.markdown(insight(
        f"Peak spend was <b>{fmt_usd(peak['spend'])}</b> on <b>{peak['date'].strftime('%b %d')}</b>. "
        f"Average daily spend across the period: <b>{fmt_usd(avg)}</b>."
    ), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(sec("Spend by Model"), unsafe_allow_html=True)
    _, pie_col, _ = st.columns([1, 2, 1])
    with pie_col:
        by_model = df.groupby("model")["spend"].sum().reset_index()
        total_m  = by_model["spend"].sum()
        by_model["pct"] = by_model["spend"] / total_m * 100
        main    = by_model[by_model["pct"] >= 2].copy()
        other_s = by_model[by_model["pct"] < 2]["spend"].sum()
        if other_s > 0:
            main = pd.concat(
                [main, pd.DataFrame([{"model": "Other", "spend": other_s, "pct": other_s / total_m * 100}])],
                ignore_index=True,
            )
        main = main.sort_values("spend", ascending=False).reset_index(drop=True)
        fig2 = go.Figure(go.Pie(
            labels=main["model"], values=main["spend"],
            hole=0.52,
            marker=dict(colors=SEQ[:len(main)], line=dict(color="#F4F7FF", width=3)),
            hovertemplate="<b>%{label}</b><br>$%{value:.4f}<br>%{percent}<extra></extra>",
            textinfo="percent",
            textfont=dict(size=13, color="white"),
            insidetextorientation="radial",
        ))
        fig2.update_layout(
            **{**_PL, "margin": dict(t=45, b=80, l=10, r=10)},
            height=380, showlegend=True,
            legend=dict(
                orientation="h",
                y=-0.22, x=0.5, xanchor="center",
                font=dict(size=14, color=C["text"]),
                bgcolor="rgba(0,0,0,0)",
            ),
            annotations=[dict(
                text=f"<b>{len(main)}</b><br><span style='font-size:11px'>models</span>",
                x=0.5, y=0.5, font_size=14, showarrow=False, font_color=C["primary"],
            )],
        )
        _style(fig2)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(sec("Daily Requests by Status"), unsafe_allow_html=True)
    dr_piv = df.groupby(["date", "status"]).size().unstack(fill_value=0).reset_index()
    dr_piv["date"] = pd.to_datetime(dr_piv["date"])
    if "success" not in dr_piv: dr_piv["success"] = 0
    if "failure" not in dr_piv: dr_piv["failure"] = 0

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=dr_piv["date"], y=dr_piv["success"], name="success",
        marker_color=C["primary"],
        customdata=dr_piv[["success", "failure"]].values,
        hovertemplate="<b>%{x|%b %d}</b><br>S: %{customdata[0]:,}<br>F: %{customdata[1]:,}<extra></extra>",
    ))
    fig3.add_trace(go.Bar(
        x=dr_piv["date"], y=dr_piv["failure"], name="failure",
        marker_color=C["pink"],
        customdata=dr_piv[["success", "failure"]].values,
        hovertemplate="<b>%{x|%b %d}</b><br>S: %{customdata[0]:,}<br>F: %{customdata[1]:,}<extra></extra>",
    ))
    fig3.update_layout(**{**_PL, "margin": dict(t=45, b=100, l=10, r=10)}, height=340,
                       barmode="stack",
                       legend=dict(orientation="h", y=-0.38, x=0.5, xanchor="center",
                                   font=dict(size=14, color=C["text"]),
                                   bgcolor="rgba(0,0,0,0)"),
                       xaxis=dict(
                           title=dict(text="Date", font=dict(size=13, color=C["muted"])),
                           showgrid=False,
                           tickformat="%b %d",
                           tickfont=dict(size=12, color=C["text_md"]),
                       ),
                       yaxis=dict(
                           title=dict(text="Number of Requests", font=dict(size=13, color=C["muted"])),
                           gridcolor="#E8EEFF",
                           tickfont=dict(size=12, color=C["text_md"]),
                       ))
    _style(fig3)
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown(sec("Spend by User"), unsafe_allow_html=True)
    by_user = df.groupby("user")["spend"].sum().sort_values(ascending=True).reset_index()
    n_users = len(by_user)
    fig4 = go.Figure(go.Bar(
        x=by_user["spend"], y=by_user["user"],
        orientation="h",
        marker=dict(color=SEQ[:n_users] if n_users <= len(SEQ) else SEQ * (n_users // len(SEQ) + 1)),
        hovertemplate="<b>%{y}</b><br>$%{x:.5f}<extra></extra>",
        text=[fmt_usd(v) for v in by_user["spend"]],
        textposition="auto",
        insidetextanchor="middle",
    ))
    bar_height = max(320, n_users * 42)
    fig4.update_layout(**_PL, height=bar_height,
                       xaxis=dict(
                           title=dict(text="Total Spend (USD)", font=dict(size=13, color=C["muted"])),
                           tickprefix="$",
                           showgrid=False,
                           tickfont=dict(size=12, color=C["text_md"]),
                       ),
                       yaxis=dict(
                           title=dict(text="User", font=dict(size=13, color=C["muted"])),
                           showgrid=False,
                           tickfont=dict(size=12, color=C["text_md"]),
                       ))
    _style(fig4)
    st.plotly_chart(fig4, use_container_width=True)



# TAB 2 - COST EXPLORER
with t2:
    st.markdown(sec("Cost Breakdown - Click to Drill In"), unsafe_allow_html=True)
    tm = df.groupby(["user", "model"])["spend"].sum().reset_index()
    tm = tm[tm["spend"] > 0]
    fig_tm = px.treemap(
        tm, path=["user", "model"], values="spend",
        color="spend",
        color_continuous_scale=[
            [0, C["sail_lt"]], [0.4, C["sail"]], [0.75, C["primary"]], [1, C["primary_dk"]]
        ],
    )
    fig_tm.update_traces(
        hovertemplate="<b>%{label}</b><br>$%{value:.5f}<extra></extra>",
        textfont=dict(size=15),
        marker_line_width=2,
        marker_line_color=C["bg"],
    )
    fig_tm.update_layout(
        **{**_PL, "uniformtext": dict(minsize=11, mode="hide")},
        height=500, coloraxis_showscale=False,
    )
    _style(fig_tm)
    st.plotly_chart(fig_tm, use_container_width=True)
    st.markdown(insight(
        "Each box is one user and model combination. Bigger box means more spend. "
        "Click any user to zoom in. Click the breadcrumb to zoom back out."
    ), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(sec("Cost Per Request by Model"), unsafe_allow_html=True)
        fig_box = px.box(
            df[df["spend"] > 0], x="model", y="spend",
            color="model", color_discrete_sequence=SEQ,
            points="outliers",
        )
        fig_box.update_layout(**_PL, height=420, showlegend=False,
                              xaxis=dict(
                                  title=dict(text="Model", font=dict(size=13, color=C["muted"])),
                                  showgrid=False, tickfont=dict(size=12, color=C["text_md"])),
                              yaxis=dict(
                                  title=dict(text="Spend per Request (USD)", font=dict(size=13, color=C["muted"])),
                                  tickprefix="$", gridcolor="#E8EEFF", tickfont=dict(size=12, color=C["text_md"])))
        _style(fig_box)
        st.plotly_chart(fig_box, use_container_width=True)

    with c2:
        st.markdown(sec("Monthly Burn Rate"), unsafe_allow_html=True)
        monthly = df.groupby("month")["spend"].sum().reset_index()
        for mo in ["January", "February", "March"]:
            if mo not in monthly["month"].values:
                monthly = pd.concat(
                    [monthly, pd.DataFrame([{"month": mo, "spend": 0}])], ignore_index=True
                )
        monthly["month"] = pd.Categorical(
            monthly["month"], categories=["January", "February", "March"], ordered=True
        )
        monthly = monthly.sort_values("month")
        fig_mo = px.bar(monthly, x="month", y="spend",
                        color="month",
                        color_discrete_sequence=[C["primary"], C["sail"], C["pink"]])
        fig_mo.update_layout(**_PL, height=420, showlegend=False,
                             xaxis=dict(
                                 title=dict(text="Month", font=dict(size=13, color=C["muted"])),
                                 showgrid=False, tickfont=dict(size=12, color=C["text_md"])),
                             yaxis=dict(
                                 title=dict(text="Total Spend (USD)", font=dict(size=13, color=C["muted"])),
                                 tickprefix="$", gridcolor="#E8EEFF", tickfont=dict(size=12, color=C["text_md"])))
        fig_mo.update_traces(hovertemplate="<b>%{x}</b><br>$%{y:.4f}<extra></extra>")
        _style(fig_mo)
        st.plotly_chart(fig_mo, use_container_width=True)
        st.markdown(insight(
            "Burn rate is the total dollars spent on LLM API calls per calendar month."
        ), unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="div"></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(sec("What-If Calculator - What if everything ran on the cheapest model (Claude Haiku)?"), unsafe_allow_html=True)
    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)

    non_haiku  = df[df["model"] != "Claude Haiku"]
    actual_nh  = non_haiku["spend"].sum()
    haiku_nh   = non_haiku["spend_haiku"].sum()
    savings_wh = actual_nh - haiku_nh
    pct_saved  = (savings_wh / actual_nh * 100) if actual_nh > 0 else 0

    w1, w2, w3 = st.columns(3)
    w1.markdown(kpi("Current Spend (non-Haiku)", fmt_usd(actual_nh),  "Sonnet and Bedrock requests"), unsafe_allow_html=True)
    w2.markdown(kpi("If All Used Cheapest Model", fmt_usd(haiku_nh),  "same token counts, Haiku rates"), unsafe_allow_html=True)
    w3.markdown(kpi("Max Potential Savings",       fmt_usd(savings_wh), f"approx. {pct_saved:.0f}% reduction"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(insight(
        "<b>Ceiling estimate only.</b> The cheapest model is faster and lower cost but may be less capable for complex tasks. "
        "Use this to identify which workloads could tolerate a model downgrade. "
        f"Even migrating half of non-Haiku requests would save approx. <b>{fmt_usd(savings_wh/2)}</b>."
    ), unsafe_allow_html=True)


# TAB 3 - TIME INTELLIGENCE
with t3:
    st.markdown(sec("Spend Calendar - Jan to Mar 2026"), unsafe_allow_html=True)

    all_dates = pd.date_range("2026-01-01", "2026-03-31")
    daily_sp  = df.groupby("date")["spend"].sum()
    cal = pd.DataFrame({"dt": all_dates})
    cal["d"]     = cal["dt"].dt.date
    cal["spend"] = cal["d"].map(daily_sp).fillna(0)
    cal["week"]  = cal["dt"].dt.isocalendar().week.astype(int)
    cal["dow"]   = cal["dt"].dt.dayofweek

    piv      = cal.pivot_table(index="dow", columns="week", values="spend", fill_value=0)
    dow_lbls = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    fig_cal = go.Figure(go.Heatmap(
        z=piv.values,
        x=[f"W{w}" for w in piv.columns],
        y=dow_lbls,
        colorscale=[
            [0, C["border"]],
            [0.2, C["sail_lt"]],
            [0.55, C["sail"]],
            [0.8, C["primary"]],
            [1, C["primary_dk"]],
        ],
        hovertemplate="<b>%{x}</b> - %{y}<br>$%{z:.4f}<extra></extra>",
        showscale=True,
        xgap=4, ygap=4,
        colorbar=dict(thickness=12, len=0.7, tickprefix="$", outlinewidth=0),
    ))
    fig_cal.update_layout(**_PL, height=245,
                          yaxis=dict(autorange="reversed", tickfont=dict(size=12, color=C["text_md"])),
                          xaxis=dict(tickfont=dict(size=11, color=C["text_md"])))
    _style(fig_cal)
    st.plotly_chart(fig_cal, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(sec("Hour-of-Day Activity (UTC)"), unsafe_allow_html=True)
        hrly = df.groupby(["hour", "model"])["spend"].sum().reset_index()
        fig_hr = px.bar(hrly, x="hour", y="spend", color="model", barmode="stack",
                        color_discrete_sequence=SEQ, labels={"model": ""})
        fig_hr.update_layout(**{**_PL, "margin": dict(t=45, b=120, l=10, r=10)}, height=360,
                             legend=dict(orientation="h", y=-0.38, x=0.5, xanchor="center",
                                         font=dict(size=14, color=C["text"]), bgcolor="rgba(0,0,0,0)"),
                             xaxis=dict(
                                 showgrid=False,
                                 title=dict(text="Hour (UTC)", font=dict(size=13, color=C["muted"])),
                                 tickmode="array",
                                 tickvals=list(range(0, 24, 2)),
                                 ticktext=[f"{h:02d}:00" for h in range(0, 24, 2)],
                                 tickfont=dict(size=11, color=C["text_md"]),
                             ),
                             yaxis=dict(
                                 tickprefix="$", gridcolor="#E8EEFF",
                                 title=dict(text="Spend (USD)", font=dict(size=13, color=C["muted"])),
                                 tickfont=dict(size=12, color=C["text_md"]),
                             ))
        _style(fig_hr)
        st.plotly_chart(fig_hr, use_container_width=True)
        peak_hr = df.groupby("hour")["spend"].sum().idxmax()
        st.markdown(insight(
            f"Peak activity is around <b>{peak_hr:02d}:00 UTC</b>. "
            f"Requests outside business hours often indicate automated pipelines or overseas users."
        ), unsafe_allow_html=True)

    with c2:
        st.markdown(sec("Day-of-Week Pattern"), unsafe_allow_html=True)
        DOW_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_d = df.groupby("dow")["spend"].sum().reset_index()
        dow_d["dow"] = pd.Categorical(dow_d["dow"], categories=DOW_ORDER, ordered=True)
        dow_d = dow_d.sort_values("dow")
        fig_dow = px.bar(dow_d, x="dow", y="spend",
                         color="dow", color_discrete_sequence=SEQ)
        fig_dow.update_layout(**{**_PL, "margin": dict(t=45, b=120, l=10, r=10)}, height=360, showlegend=False,
                              xaxis=dict(
                                  showgrid=False,
                                  title=dict(text="Day of Week", font=dict(size=13, color=C["muted"])),
                                  tickfont=dict(size=12, color=C["text_md"]),
                              ),
                              yaxis=dict(
                                  tickprefix="$", gridcolor="#E8EEFF",
                                  title=dict(text="Spend (USD)", font=dict(size=13, color=C["muted"])),
                                  tickfont=dict(size=12, color=C["text_md"]),
                              ))
        fig_dow.update_traces(hovertemplate="<b>%{x}</b><br>$%{y:.4f}<extra></extra>")
        _style(fig_dow)
        st.plotly_chart(fig_dow, use_container_width=True)
        busiest  = dow_d.loc[dow_d["spend"].idxmax(), "dow"]
        wknd_pct = dow_d[dow_d["dow"].isin(["Saturday", "Sunday"])]["spend"].sum() / dow_d["spend"].sum() * 100
        st.markdown(insight(
            f"<b>{busiest}</b> is the busiest day. "
            f"Weekend activity is <b>{wknd_pct:.0f}%</b> of total, "
            f"{'suggesting mostly automated use' if wknd_pct > 20 else 'pointing to human / business-hours usage'}."
        ), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(sec("Week-over-Week Spend and Volume"), unsafe_allow_html=True)

    df["_wk"] = df["start_dt"].dt.isocalendar().week.astype(int)
    wkly = df.groupby("_wk").agg(
        spend=("spend", "sum"),
        requests=("request_id", "count"),
    ).reset_index(names="week_num")

    fig_wk = make_subplots(specs=[[{"secondary_y": True}]])
    fig_wk.add_trace(go.Bar(x=wkly["week_num"], y=wkly["spend"],
                            name="Spend", marker_color=C["sail_lt"],
                            hovertemplate="Week %{x}<br>$%{y:.4f}<extra></extra>"),
                     secondary_y=False)
    fig_wk.add_trace(go.Scatter(x=wkly["week_num"], y=wkly["requests"],
                                name="Requests", line=dict(color=C["pink"], width=2.5),
                                hovertemplate="Week %{x}<br>%{y:,} requests<extra></extra>"),
                     secondary_y=True)
    fig_wk.update_layout(**{**_PL, "margin": dict(t=45, b=80, l=10, r=10)}, height=320,
                         legend=dict(orientation="h", y=-0.28, x=0.5, xanchor="center",
                                     font=dict(size=14, color=C["text"]), bgcolor="rgba(0,0,0,0)"))
    fig_wk.update_yaxes(tickprefix="$", gridcolor="#E8EEFF",
                        title_text="Weekly Spend (USD)", title_font=dict(size=13, color=C["muted"]),
                        tickfont=dict(size=12, color=C["text_md"]), secondary_y=False)
    fig_wk.update_yaxes(showgrid=False,
                        title_text="Number of Requests", title_font=dict(size=13, color=C["muted"]),
                        tickfont=dict(size=12, color=C["text_md"]), secondary_y=True)
    fig_wk.update_xaxes(title_text="Week Number", title_font=dict(size=13, color=C["muted"]),
                        tickfont=dict(size=12, color=C["text_md"]), showgrid=False)
    _style(fig_wk)
    st.plotly_chart(fig_wk, use_container_width=True)


# TAB 4 - USERS
with t4:
    st.markdown(sec("User Leaderboard"), unsafe_allow_html=True)
    st.markdown(f"""
    <div style='display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1.2rem'>
      <div style='flex:1;min-width:180px;background:{C["card"]};border:1px solid {C["border"]};
                  border-radius:12px;padding:0.9rem 1.1rem'>
        <div style='font-size:0.7rem;font-weight:700;color:{C["muted"]};text-transform:uppercase;
                    letter-spacing:0.08em;margin-bottom:0.3rem'>Spend</div>
        <div style='font-size:0.85rem;color:{C["text_md"]}'>Total dollars billed to this user's API key.
        Sorted by this column, highest first.</div>
      </div>
      <div style='flex:1;min-width:180px;background:{C["card"]};border:1px solid {C["border"]};
                  border-radius:12px;padding:0.9rem 1.1rem'>
        <div style='font-size:0.7rem;font-weight:700;color:{C["muted"]};text-transform:uppercase;
                    letter-spacing:0.08em;margin-bottom:0.3rem'>Tokens</div>
        <div style='font-size:0.85rem;color:{C["text_md"]}'>Total tokens consumed (prompt + completion + cached).
        Output tokens shown separately as they cost more.</div>
      </div>
      <div style='flex:1;min-width:180px;background:{C["card"]};border:1px solid {C["border"]};
                  border-radius:12px;padding:0.9rem 1.1rem'>
        <div style='font-size:0.7rem;font-weight:700;color:{C["muted"]};text-transform:uppercase;
                    letter-spacing:0.08em;margin-bottom:0.3rem'>Avg Latency</div>
        <div style='font-size:0.85rem;color:{C["text_md"]}'>Average seconds from request sent to response received.
        Higher latency often means longer outputs or a larger model.</div>
      </div>
      <div style='flex:1;min-width:180px;background:{C["card"]};border:1px solid {C["border"]};
                  border-radius:12px;padding:0.9rem 1.1rem'>
        <div style='font-size:0.7rem;font-weight:700;color:{C["muted"]};text-transform:uppercase;
                    letter-spacing:0.08em;margin-bottom:0.3rem'>Efficiency Score</div>
        <div style='font-size:0.85rem;color:{C["text_md"]}'>0-100 composite: 50% cache savings ratio,
        50% output tokens per dollar. Higher is better.</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    us = df.groupby("user").agg(
        spend=("spend", "sum"),
        requests=("request_id", "count"),
        sessions=("session_id", "nunique"),
        total_tokens=("total_tokens", "sum"),
        completion_tokens=("completion_tokens", "sum"),
        avg_latency=("latency", "mean"),
        failures=("status", lambda x: (x == "failure").sum()),
        cache_savings=("cache_savings", "sum"),
    ).reset_index().sort_values("spend", ascending=False).reset_index(drop=True)

    us["cost_per_req"]      = us["spend"] / us["requests"].clip(1)
    us["output_per_dollar"] = us["completion_tokens"] / us["spend"].clip(1e-9)
    us["failure_rate"]      = us["failures"] / us["requests"].clip(1) * 100
    us["efficiency"]        = (
        (us["cache_savings"] / us["spend"].clip(1e-9)).clip(0, 1) * 50
        + (us["output_per_dollar"] / us["output_per_dollar"].max()) * 50
    ).clip(0, 100).round(1)

    rank_classes = ["gold", "silver", "bronze"] + [""] * 50
    rank_labels  = ["#1", "#2", "#3"] + [f"#{i}" for i in range(4, 55)]

    for idx, row in us.iterrows():
        rc    = rank_classes[idx]
        rl    = rank_labels[idx]
        mc, uc, sc1, sc2, sc3, sc4 = st.columns([0.25, 1.6, 1, 1, 1, 1])
        mc.markdown(f"<div style='padding-top:0.5rem'><span class='rank {rc}'>{rl}</span></div>",
                    unsafe_allow_html=True)
        uc.markdown(
            f"<div style='font-weight:700;color:{C['text']};font-size:1rem;padding-top:0.55rem'>"
            f"{row['user']}</div>"
            f"<div style='font-size:0.74rem;color:{C['muted']}'>"
            f"{row['requests']:,} requests, {row['sessions']:,} sessions</div>",
            unsafe_allow_html=True,
        )
        sc1.markdown(kpi("Spend",       fmt_usd(row["spend"]),        fmt_usd(row["cost_per_req"]) + " per req"), unsafe_allow_html=True)
        sc2.markdown(kpi("Tokens",      fmt_k(row["total_tokens"]),   f"{fmt_k(row['completion_tokens'])} output"), unsafe_allow_html=True)
        sc3.markdown(kpi("Avg Latency", f"{row['avg_latency']:.1f}s", f"{row['failure_rate']:.0f}% failure rate"), unsafe_allow_html=True)
        sc4.markdown(kpi("Efficiency",  f"{row['efficiency']:.0f}/100", "cache and output score"), unsafe_allow_html=True)
        st.markdown("<div class='lr'></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(sec("User Deep Dive"), unsafe_allow_html=True)
    sel_user = st.selectbox("Select a user", sorted(df["user"].unique()),
                            label_visibility="collapsed")
    udf = df[df["user"] == sel_user]

    uc1, uc2, uc3 = st.columns(3)
    with uc1:
        st.markdown(sec("Daily Spend"), unsafe_allow_html=True)
        ud = udf.groupby("date")["spend"].sum().reset_index()
        ud["date"] = pd.to_datetime(ud["date"])
        fig_u1 = px.area(ud, x="date", y="spend", color_discrete_sequence=[C["primary"]])
        fig_u1.update_traces(fillcolor="rgba(101,113,255,0.12)")
        fig_u1.update_layout(**_PL, height=235,
                             yaxis=dict(
                                 tickprefix="$", gridcolor="#E8EEFF",
                                 title=dict(text="Spend (USD)", font=dict(size=12, color=C["muted"])),
                                 tickfont=dict(size=11, color=C["text_md"]),
                             ),
                             xaxis=dict(
                                 showgrid=False,
                                 title=dict(text="Date", font=dict(size=12, color=C["muted"])),
                                 tickformat="%b %d",
                                 tickfont=dict(size=11, color=C["text_md"]),
                             ))
        _style(fig_u1)
        st.plotly_chart(fig_u1, use_container_width=True)

    with uc2:
        st.markdown(sec("Model Mix"), unsafe_allow_html=True)
        um = udf.groupby("model")["spend"].sum().reset_index()
        fig_u2 = go.Figure(go.Pie(
            labels=um["model"], values=um["spend"], hole=0.5,
            marker=dict(colors=SEQ, line=dict(color=C["bg"], width=2)),
            textinfo="percent", textfont_size=14,
        ))
        fig_u2.update_layout(**{**_PL, "margin": dict(t=45, b=70, l=10, r=10)},
                             height=270, showlegend=True,
                             legend=dict(
                                 orientation="h", y=-0.25, x=0.5, xanchor="center",
                                 font=dict(size=14, color=C["text"]),
                                 bgcolor="rgba(0,0,0,0)",
                             ))
        st.plotly_chart(fig_u2, use_container_width=True)

    with uc3:
        st.markdown(sec("Token Mix"), unsafe_allow_html=True)
        tok = pd.DataFrame({
            "type":   ["Prompt", "Completion", "Cache Read", "Cache Create"],
            "tokens": [udf["prompt_tokens"].sum(), udf["completion_tokens"].sum(),
                       udf["cache_read"].sum(),     udf["cache_create"].sum()],
        })
        tok = tok[tok["tokens"] > 0]
        fig_u3 = px.bar(
            tok, x="type", y="tokens", color="type",
            color_discrete_sequence=[C["primary"], C["pink"], C["sail"], C["sail_lt"]],
            text=tok["tokens"].apply(fmt_k),
        )
        fig_u3.update_traces(textposition="outside", textfont=dict(size=11, color=C["text_md"]))
        fig_u3.update_layout(**_PL, height=280, showlegend=False,
                             xaxis=dict(
                                 showgrid=False,
                                 title=dict(text="Token Type", font=dict(size=12, color=C["muted"])),
                                 tickfont=dict(size=11, color=C["text_md"]),
                             ),
                             yaxis=dict(
                                 type="log",
                                 gridcolor="#E8EEFF",
                                 title=dict(text="Tokens (log scale)", font=dict(size=12, color=C["muted"])),
                                 tickfont=dict(size=11, color=C["text_md"]),
                             ))
        _style(fig_u3)
        st.plotly_chart(fig_u3, use_container_width=True)

    u_row      = us[us["user"] == sel_user].iloc[0]
    cache_pct_u = udf["cache_read"].sum() / udf["prompt_tokens"].sum() * 100 if udf["prompt_tokens"].sum() > 0 else 0
    st.markdown(insight(
        f"<b>{sel_user}</b> spent <b>{fmt_usd(u_row['spend'])}</b> across "
        f"<b>{int(u_row['requests']):,}</b> requests. "
        f"Cache hit rate: <b>{cache_pct_u:.1f}%</b>. "
        f"Failure rate: <b>{u_row['failure_rate']:.1f}%</b>. "
        f"Average response time: <b>{u_row['avg_latency']:.1f}s</b>."
    ), unsafe_allow_html=True)


# TAB 5 - CACHE
with t5:
    tc_read   = df["cache_read"].sum()
    tc_create = df["cache_create"].sum()
    tc_save   = df["cache_savings"].sum()
    tc_pct    = tc_read / df["prompt_tokens"].sum() * 100 if df["prompt_tokens"].sum() > 0 else 0

    ban_col, ill_col = st.columns([3, 1])
    with ban_col:
        st.markdown(f"""
        <div class="savings-banner">
          <div style='display:flex;gap:3rem;align-items:flex-start'>
            <div>
              <div class="savings-lbl">Total Cache Savings</div>
              <div class="savings-big">{fmt_usd(tc_save)}</div>
              <div class="savings-note">estimated reduction vs. billing all prompt tokens at standard (non-cached) input rates</div>
            </div>
            <div>
              <div class="savings-lbl">Cache Hit Rate</div>
              <div class="savings-big" style="font-size:2.3rem">{tc_pct:.1f}%</div>
              <div style="color:rgba(255,255,255,0.6);font-size:0.83rem">
                {fmt_k(tc_read)} tokens served from cache
              </div>
            </div>
            <div>
              <div class="savings-lbl">Cache Created</div>
              <div class="savings-big" style="font-size:2.3rem">{fmt_k(tc_create)}</div>
              <div style="color:rgba(255,255,255,0.6);font-size:0.83rem">
                tokens written to cache
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with ill_col:
        st.markdown(
            f"<div style='text-align:center;padding-top:0.5rem;opacity:0.9'>{SVG_CACHE}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(sec("Cache Read Tokens vs. Cache % (daily)"), unsafe_allow_html=True)
    dc = df.groupby("date").agg(
        cache_read=("cache_read", "sum"),
        prompt=("prompt_tokens", "sum"),
    ).reset_index()
    dc["date"]      = pd.to_datetime(dc["date"])
    dc["cache_pct"] = dc["cache_read"] / dc["prompt"].clip(1) * 100

    fig_c1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig_c1.add_trace(go.Bar(x=dc["date"], y=dc["cache_read"],
                            name="Cached Tokens", marker_color=C["sail_lt"],
                            hovertemplate="%{x|%b %d}<br>%{y:,.0f} tokens<extra></extra>"),
                     secondary_y=False)
    fig_c1.add_trace(go.Scatter(x=dc["date"], y=dc["cache_pct"],
                                name="Cache %", line=dict(color=C["pink"], width=2.5),
                                hovertemplate="%{x|%b %d}<br>%{y:.1f}%<extra></extra>"),
                     secondary_y=True)
    fig_c1.update_layout(**_PL)
    fig_c1.update_yaxes(gridcolor="#E8EEFF", title_text="Cached Tokens", zeroline=False, secondary_y=False)
    fig_c1.update_yaxes(ticksuffix="%", showgrid=False, title_text="Cache Hit %", zeroline=False, secondary_y=True)
    fig_c1.update_xaxes(showline=False, zeroline=False)
    fig_c1.update_xaxes(tickformat="%b %d")
    _style(fig_c1, height=320, legend="below")
    st.plotly_chart(fig_c1, use_container_width=True)

    st.markdown(sec("Cache Efficiency by User"), unsafe_allow_html=True)
    uc = df.groupby("user").agg(
        cache_read=("cache_read", "sum"),
        prompt=("prompt_tokens", "sum"),
        savings=("cache_savings", "sum"),
    ).reset_index()
    uc["cache_pct"] = uc["cache_read"] / uc["prompt"].clip(1) * 100
    uc = uc.sort_values("cache_pct", ascending=True)
    n_uc = len(uc)

    fig_c2 = go.Figure(go.Bar(
        x=uc["cache_pct"], y=uc["user"],
        orientation="h",
        marker=dict(
            color=uc["cache_pct"].tolist(),
            colorscale=[[0, C["pink_lt"]], [0.5, C["sail"]], [1, C["primary"]]],
            showscale=False,
        ),
        text=[f"{v:.0f}%" for v in uc["cache_pct"]],
        textposition="auto",
        insidetextanchor="middle",
        hovertemplate="<b>%{y}</b><br>Cache rate: %{x:.1f}%<extra></extra>",
    ))
    fig_c2.update_layout(**_PL,
                         xaxis=dict(ticksuffix="%", range=[0, 115], showgrid=False,
                                    title=dict(text="Cache Hit Rate", font=dict(size=13, color=C["muted"])),
                                    tickfont=dict(size=12, color=C["text_md"])),
                         yaxis=dict(showgrid=False,
                                    title=dict(text="User", font=dict(size=13, color=C["muted"])),
                                    tickfont=dict(size=12, color=C["text_md"])))
    _style(fig_c2, height=max(320, n_uc * 42), legend="none")
    st.plotly_chart(fig_c2, use_container_width=True)

    best  = uc.loc[uc["cache_pct"].idxmax()]
    worst = uc.loc[uc["cache_pct"].idxmin()]
    st.markdown(insight(
        f"<b>{best['user']}</b> has the highest cache utilization at <b>{best['cache_pct']:.0f}%</b>, "
        f"saving <b>{fmt_usd(best['savings'])}</b>. "
        f"<b>{worst['user']}</b> caches only <b>{worst['cache_pct']:.0f}%</b> of prompt tokens. "
        f"Enabling session-based caching could significantly cut their costs."
    ), unsafe_allow_html=True)

    if df["reasoning_tokens"].sum() > 0:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(sec("Extended Thinking - Reasoning Tokens"), unsafe_allow_html=True)
        rt = df[df["reasoning_tokens"] > 0].groupby("date")["reasoning_tokens"].sum().reset_index()
        rt["date"] = pd.to_datetime(rt["date"])
        fig_rt = px.bar(rt, x="date", y="reasoning_tokens",
                        color_discrete_sequence=[C["primary_dk"]])
        fig_rt.update_layout(**_PL,
                             xaxis=dict(showgrid=False,
                                        title=dict(text="Date", font=dict(size=13, color=C["muted"])),
                                        tickformat="%b %d",
                                        tickfont=dict(size=12, color=C["text_md"])),
                             yaxis=dict(gridcolor="#E8EEFF",
                                        title=dict(text="Reasoning Tokens", font=dict(size=13, color=C["muted"])),
                                        tickfont=dict(size=12, color=C["text_md"])))
        _style(fig_rt, height=220, legend="none")
        st.plotly_chart(fig_rt, use_container_width=True)


# TAB 6 - SESSIONS
with t6:
    sdf = df[df["session_id"].notna() & (df["session_id"] != "")].copy()

    if sdf.empty:
        st.info("No session data available in the current filter.")
    else:
        ss = sdf.groupby("session_id").agg(
            turns=("request_id", "count"),
            spend=("spend", "sum"),
            total_tokens=("total_tokens", "sum"),
            user=("user", "first"),
            model=("model", "first"),
            start=("start_dt", "min"),
            end=("end_dt", "max"),
        ).reset_index()
        ss["duration_min"] = (ss["end"] - ss["start"]).dt.total_seconds() / 60
        ss = ss[ss["duration_min"] >= 0]

        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(kpi("Sessions",        f"{len(ss):,}",                        "unique session IDs"),       unsafe_allow_html=True)
        k2.markdown(kpi("Avg Turns",        f"{ss['turns'].mean():.1f}",           f"max {ss['turns'].max()}"), unsafe_allow_html=True)
        k3.markdown(kpi("Avg Session Cost", fmt_usd(ss["spend"].mean()),            f"median {fmt_usd(ss['spend'].median())}"), unsafe_allow_html=True)
        k4.markdown(kpi("Avg Duration",     f"{ss['duration_min'].mean():.1f} min", f"max {ss['duration_min'].max():.0f} min"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)

        with c1:
            st.markdown(sec("Turns per Session"), unsafe_allow_html=True)
            fig_s1 = px.histogram(ss, x="turns", nbins=25,
                                   color_discrete_sequence=[C["primary"]])
            fig_s1.update_layout(**_PL,
                                 xaxis=dict(title=dict(text="Turns per Session", font=dict(size=13, color=C["muted"])),
                                            showgrid=False, tickfont=dict(size=12, color=C["text_md"])),
                                 yaxis=dict(title=dict(text="Number of Sessions", font=dict(size=13, color=C["muted"])),
                                            gridcolor="#E8EEFF", tickfont=dict(size=12, color=C["text_md"])))
            _style(fig_s1, height=280, legend="none")
            st.plotly_chart(fig_s1, use_container_width=True)

        with c2:
            st.markdown(sec("Cost vs. Session Length (bubble = tokens)"), unsafe_allow_html=True)
            fig_s2 = px.scatter(
                ss[ss["spend"] > 0],
                x="turns", y="spend",
                color="user", size="total_tokens",
                size_max=30,
                color_discrete_sequence=SEQ,
                hover_data={"session_id": True, "user": True, "turns": True},
            )
            fig_s2.update_layout(**_PL,
                                 xaxis=dict(title=dict(text="Turns", font=dict(size=13, color=C["muted"])),
                                            showgrid=False, tickfont=dict(size=12, color=C["text_md"])),
                                 yaxis=dict(title=dict(text="Spend (USD)", font=dict(size=13, color=C["muted"])),
                                            tickprefix="$", gridcolor="#E8EEFF", tickfont=dict(size=12, color=C["text_md"])))
            _style(fig_s2, height=280, legend="below")
            st.plotly_chart(fig_s2, use_container_width=True)

        st.markdown(sec("Response Latency Distribution"), unsafe_allow_html=True)
        lat = df[df["latency"] > 0]
        fig_lat = px.histogram(lat, x="latency", color="model", nbins=50,
                               barmode="overlay", opacity=0.75,
                               color_discrete_sequence=SEQ)
        fig_lat.update_layout(**_PL,
                              xaxis=dict(title=dict(text="Latency (seconds)", font=dict(size=13, color=C["muted"])),
                                         showgrid=False, tickfont=dict(size=12, color=C["text_md"])),
                              yaxis=dict(title=dict(text="Count", font=dict(size=13, color=C["muted"])),
                                         gridcolor="#E8EEFF", tickfont=dict(size=12, color=C["text_md"])))
        _style(fig_lat, height=300, legend="below")
        st.plotly_chart(fig_lat, use_container_width=True)

        p50 = lat["latency"].quantile(0.5)
        p95 = lat["latency"].quantile(0.95)
        p99 = lat["latency"].quantile(0.99)
        st.markdown(insight(
            f"Median response: <b>{p50:.1f}s</b>, P95: <b>{p95:.1f}s</b>, P99: <b>{p99:.1f}s</b>. "
            f"Long tails typically indicate large context windows or extended-thinking requests."
        ), unsafe_allow_html=True)


# TAB 7 - ASK THE DATA
with t7:
    ask_c1, ask_c2 = st.columns([3, 1])
    with ask_c1:
        st.markdown(f"""
        <div class="ai-header">
          <div style='font-size:1.45rem;font-weight:800;color:{C["text"]};letter-spacing:-0.01em'>
            Ask Anything About Your Data
          </div>
          <div style='color:{C["muted"]};font-size:0.9rem;margin-top:0.35rem;line-height:1.65'>
            Type a question in plain English. No SQL, no code needed.
            The AI reads your <b style='color:{C["primary"]}'>{len(df):,} filtered requests</b>
            and answers directly. Use the sidebar to narrow the data first.
          </div>
        </div>
        """, unsafe_allow_html=True)
    with ask_c2:
        st.markdown(
            f"<div style='text-align:center;opacity:0.9;padding-top:0.3rem'>{SVG_AI_BOT}</div>",
            unsafe_allow_html=True,
        )

    EXAMPLE_QS = [
        "Who spent the most overall?",
        "Which model is best value?",
        "Any spending spikes?",
        "Cache hit rate trend?",
        "Busiest day of week?",
        "Who is most efficient?",
    ]

    st.markdown(
        f"<div style='font-size:0.82rem;color:{C['muted']};margin-bottom:0.5rem;font-weight:500'>Try one of these:</div>",
        unsafe_allow_html=True,
    )
    # Pop chip question set on previous run before rendering text input
    chip_q = st.session_state.pop("_chip_question", None)

    chip_cols = st.columns(len(EXAMPLE_QS))
    for col, q in zip(chip_cols, EXAMPLE_QS):
        if col.button(q, key=f"q_{q[:14]}", use_container_width=True):
            st.session_state["_chip_question"] = q
            st.rerun()

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
    user_q = st.text_input(
        "Question",
        value=chip_q or "",
        placeholder='e.g. "Which user had the biggest January spike and why might that be?"',
        label_visibility="collapsed",
    )

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    ask_btn = st.button("Analyze", type="primary")

    run_q    = chip_q or (user_q if ask_btn else None)

    if run_q:
        if not api_key:
            st.warning("ANTHROPIC_API_KEY environment variable is not set.")
        else:
            summary = {
                "period":               f"{df['date'].min()} to {df['date'].max()}",
                "total_requests":       len(df),
                "total_spend_usd":      round(df["spend"].sum(), 6),
                "users":                df["user"].unique().tolist(),
                "spend_by_user":        df.groupby("user")["spend"].sum().round(6).to_dict(),
                "requests_by_user":     df.groupby("user").size().to_dict(),
                "spend_by_model":       df.groupby("model")["spend"].sum().round(6).to_dict(),
                "spend_by_month":       df.groupby("month")["spend"].sum().round(6).to_dict(),
                "daily_spend_top20":    {
                    str(k): round(v, 6)
                    for k, v in df.groupby("date")["spend"].sum()
                    .sort_values(ascending=False).head(20).items()
                },
                "total_tokens":         int(df["total_tokens"].sum()),
                "cache_read_tokens":    int(df["cache_read"].sum()),
                "cache_savings_usd":    round(df["cache_savings"].sum(), 6),
                "cache_pct_by_user":    (
                    (df.groupby("user")["cache_read"].sum()
                     / df.groupby("user")["prompt_tokens"].sum() * 100).round(1).to_dict()
                ),
                "avg_latency_s":        round(df["latency"].mean(), 2),
                "failure_rate_pct":     round((df["status"] == "failure").mean() * 100, 2),
                "requests_by_dow":      df.groupby("dow").size().to_dict(),
                "requests_by_hour":     df.groupby("hour").size().to_dict(),
                "sessions":             int(df["session_id"].nunique()),
                "reasoning_tokens":     int(df["reasoning_tokens"].sum()),
            }

            answer_slot = st.empty()
            answer_slot.markdown(f"""
            <div class="ai-answer" style="min-height:90px;display:flex;align-items:center;justify-content:center">
              <div style="display:flex;gap:8px;align-items:center">
                <span style="width:10px;height:10px;border-radius:50%;background:{C['primary']};
                             display:inline-block;animation:bounce 1.2s ease-in-out infinite"></span>
                <span style="width:10px;height:10px;border-radius:50%;background:{C['sail']};
                             display:inline-block;animation:bounce 1.2s ease-in-out 0.2s infinite"></span>
                <span style="width:10px;height:10px;border-radius:50%;background:{C['pink']};
                             display:inline-block;animation:bounce 1.2s ease-in-out 0.4s infinite"></span>
              </div>
            </div>
            <style>
              @keyframes bounce {{
                0%,80%,100% {{ transform:translateY(0); opacity:0.5 }}
                40% {{ transform:translateY(-10px); opacity:1 }}
              }}
            </style>
            """, unsafe_allow_html=True)
            try:
                client = anthropic.Anthropic(api_key=api_key)
                resp = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=600,
                    system=(
                        "You are a sharp analytics assistant for an LLM usage dashboard. "
                        "Answer questions about the data directly and concisely. "
                        "Use **bold** for key numbers and names. "
                        "Be specific and cite actual numbers. "
                        "Keep answers under 180 words. No bullet lists, flowing prose only."
                    ),
                    messages=[{
                        "role": "user",
                        "content": (
                            f"Here is a statistical summary of the LLM usage data (already filtered):\n"
                            f"```json\n{json.dumps(summary, indent=2, default=str)}\n```\n\n"
                            f"Answer this question: {run_q}"
                        ),
                    }],
                )
                answer      = resp.content[0].text
                answer_html = md_to_html(answer).replace("\n", "<br>")
                answer_slot.markdown(f"""
                <div class="ai-answer">
                  <div class="ai-lbl">AI Analysis | {len(df):,} requests | filtered view</div>
                  {answer_html}
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                answer_slot.error(f"API error: {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(insight(
        "<b>Tip:</b> Use the sidebar to filter down to one user or model, "
        "then ask what is unusual about this user for laser-focused insights."
    ), unsafe_allow_html=True)
