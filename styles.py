"""
styles.py
---------
Injects the global CSS (Poppins font, KPI cards, tabs, sidebar, etc.)
and defines the inline SVG illustrations used across tabs.

Call inject_css() once at the top of app.py, after st.set_page_config().
"""

import streamlit as st
from config import C


# ---------------------------------------------------------------------------
# Inline SVG illustrations
# ---------------------------------------------------------------------------

# Used in the Ask the Data tab header
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

# Used in the Cache tab banner
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


# ---------------------------------------------------------------------------
# Global CSS injection
# ---------------------------------------------------------------------------

def inject_css() -> None:
    """Inject all global CSS into the Streamlit page."""
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

  /* Sidebar toggle button */
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
