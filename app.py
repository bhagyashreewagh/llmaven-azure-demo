"""
LLM Spend Intelligence Dashboard
University of Washington, eScience Institute, Jan-Mar 2026

Entry point - keeps only page config, CSS injection, sidebar, and tab routing.
All logic lives in the modules listed below.

Module map
----------
config.py           - color palette, Plotly defaults, ZIP_PATH
styles.py           - global CSS + SVG illustrations
utils.py            - formatters, HTML helpers, _style()
data.py             - load_data() (cached), _clean_model(), _cache_savings()
tabs/overview.py    - Tab 1
tabs/cost_explorer.py   - Tab 2
tabs/time_intelligence.py - Tab 3
tabs/users.py       - Tab 4
tabs/cache.py       - Tab 5
tabs/sessions.py    - Tab 6
tabs/ask_the_data.py - Tab 7
"""

# ---------------------------------------------------------------------------
# Load .env before importing anything that reads env vars.
# Create a .env file in this directory with:
#   ANTHROPIC_API_KEY=sk-ant-...
#   DATA_ZIP=path/to/your/logs.zip   (optional, see config.py for default)
# ---------------------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

from config import C
from styles import inject_css
from data import load_data

import tabs.overview          as tab_overview
import tabs.cost_explorer     as tab_cost
import tabs.time_intelligence as tab_time
import tabs.users             as tab_users
import tabs.cache             as tab_cache
import tabs.sessions          as tab_sessions
import tabs.ask_the_data      as tab_ask


# ---------------------------------------------------------------------------
# Page config (must be the first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="LLM Spend Intelligence",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
df_all = load_data()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
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

    # Reset Filters uses a flag so we don't try to set widget state after render
    if st.session_state.pop("_do_reset", False):
        st.session_state["sb_users"]   = []
        st.session_state["sb_models"]  = []
        st.session_state["sb_outcome"] = []

    sel_users    = st.multiselect("Users",        sorted(df_all["user"].unique()),   placeholder="All users",          key="sb_users")
    sel_models   = st.multiselect("Models",       sorted(df_all["model"].unique()),  placeholder="All models",         key="sb_models")
    sel_statuses = st.multiselect("Call Outcome", sorted(df_all["status"].unique()), placeholder="success + failure",  key="sb_outcome")

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("Reset Filters", use_container_width=True):
        st.session_state["_do_reset"] = True
        st.rerun()


# ---------------------------------------------------------------------------
# Apply sidebar filters
# ---------------------------------------------------------------------------
def apply_filters(df):
    if len(date_range) == 2:
        df = df[(df["date"] >= date_range[0]) & (df["date"] <= date_range[1])]
    if sel_users:    df = df[df["user"].isin(sel_users)]
    if sel_models:   df = df[df["model"].isin(sel_models)]
    if sel_statuses: df = df[df["status"].isin(sel_statuses)]
    return df


df = apply_filters(df_all)


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "Overview",
    "Cost Explorer",
    "Time Intelligence",
    "Users",
    "Cache",
    "Sessions",
    "Ask the Data",
])

with t1: tab_overview.render(df)
with t2: tab_cost.render(df)
with t3: tab_time.render(df)
with t4: tab_users.render(df)
with t5: tab_cache.render(df)
with t6: tab_sessions.render(df)
with t7: tab_ask.render(df)
