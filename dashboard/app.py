"""
LLMaven Usage Dashboard
========================
Professional Streamlit dashboard for LLMaven AI usage analytics.
Reads clean Parquet files from Azure Data Lake or falls back to demo data.

Turns calculation note:
  We do NOT use len(proxy_server_request.messages) to count turns.
  Each new message in a conversation resends the entire history, so the
  message list grows each turn. Instead, turns = total number of separate
  requests that share the same session_id.
"""

import os
import io
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LLMaven · AI Usage Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0f1117; }

    /* Hide default Streamlit header/footer */
    #MainMenu, footer, header { visibility: hidden; }

    /* Top header bar */
    .top-header {
        background: linear-gradient(135deg, #1a1f2e 0%, #16213e 100%);
        border-bottom: 2px solid #2d3561;
        padding: 1.4rem 2rem;
        margin: -1rem -1rem 2rem -1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .top-header h1 {
        color: #ffffff;
        font-size: 1.7rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .top-header .subtitle {
        color: #8892b0;
        font-size: 0.85rem;
        margin-top: 0.3rem;
    }
    .badge {
        background: #2d3561;
        color: #64ffda;
        padding: 0.35rem 0.9rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid #64ffda55;
        letter-spacing: 0.5px;
    }

    /* KPI cards */
    .kpi-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #16213e 100%);
        border: 1px solid #2d3561;
        border-radius: 14px;
        padding: 1.4rem 1.5rem;
        text-align: center;
        transition: border-color 0.2s, transform 0.15s;
    }
    .kpi-card:hover {
        border-color: #64ffda88;
        transform: translateY(-2px);
    }
    .kpi-label {
        color: #8892b0;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin-bottom: 0.6rem;
    }
    .kpi-value {
        color: #ffffff;
        font-size: 2rem;
        font-weight: 800;
        line-height: 1;
    }
    .kpi-sub {
        color: #8892b0;
        font-size: 0.72rem;
        margin-top: 0.35rem;
    }
    .kpi-accent { color: #64ffda; }

    /* Section headers */
    .section-header {
        color: #ccd6f6;
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid #2d3561;
        letter-spacing: 0.2px;
    }

    /* Insight callout */
    .insight {
        background: #1a1f2e;
        border-left: 3px solid #7b61ff;
        border-radius: 0 8px 8px 0;
        padding: 0.5rem 0.9rem;
        color: #8892b0;
        font-size: 0.8rem;
        margin-bottom: 0.5rem;
    }
    .insight b { color: #ccd6f6; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #1a1f2e;
        border-right: 1px solid #2d3561;
    }
    section[data-testid="stSidebar"] .stMarkdown p {
        color: #8892b0;
        font-size: 0.8rem;
    }

    /* Demo banner */
    .demo-banner {
        background: linear-gradient(90deg, #2d3561 0%, #1a1f2e 100%);
        border: 1px solid #64ffda33;
        border-left: 3px solid #64ffda;
        border-radius: 8px;
        padding: 0.7rem 1rem;
        color: #8892b0;
        font-size: 0.85rem;
        margin-bottom: 1.5rem;
    }
    .demo-banner span { color: #64ffda; font-weight: 700; }

    /* Divider */
    hr { border-color: #2d3561 !important; }

    /* Dataframe */
    .stDataFrame { border: 1px solid #2d3561; border-radius: 8px; }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background: #1a1f2e;
        border-radius: 8px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #8892b0;
        border-radius: 6px;
    }
    .stTabs [aria-selected="true"] {
        background: #2d3561;
        color: #64ffda;
    }
</style>
""", unsafe_allow_html=True)

# ── Chart theme ────────────────────────────────────────────────────────────────
CHART_THEME = {
    "paper_bgcolor": "#1a1f2e",
    "plot_bgcolor":  "#1a1f2e",
    "font":          {"color": "#ccd6f6", "family": "Inter, sans-serif", "size": 12},
    "xaxis":         {"gridcolor": "#2d3561", "linecolor": "#2d3561", "tickfont": {"color": "#8892b0"}},
    "yaxis":         {"gridcolor": "#2d3561", "linecolor": "#2d3561", "tickfont": {"color": "#8892b0"}},
    "margin":        {"t": 30, "b": 10, "l": 10, "r": 10},
}
COLORS = ["#64ffda", "#7b61ff", "#ff6b9d", "#ffd166", "#06d6a0", "#118ab2"]

def apply_theme(fig):
    fig.update_layout(**CHART_THEME)
    return fig

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="top-header">
    <div>
        <h1>🧠 LLMaven &middot; AI Usage Dashboard</h1>
        <div class="subtitle">University of Washington &middot; eScience Institute &middot; LiteLLM spend logs</div>
    </div>
    <div class="badge">&#9679; LIVE DEMO</div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    st.markdown("---")

    date_range = st.date_input(
        "Date range",
        value=(datetime.today() - timedelta(days=30), datetime.today()),
        max_value=datetime.today(),
    )

    st.markdown("**Source filter**")
    st.caption("Uncheck SafeMind to focus on coding activity only")
    filter_source = st.multiselect(
        "Sources",
        options=["Claude-Code", "SafeMind", "curl", "python-script", "unknown"],
        default=["Claude-Code", "curl", "python-script", "unknown"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("**About**")
    st.caption("Data flows daily from LLMaven to Azure Data Lake to this dashboard. Built with Streamlit and Plotly.")
    st.caption("Currently showing **demo data**. Connect Azure Data Lake for real sessions.")
    st.markdown("---")
    st.markdown("**Turns note**")
    st.caption(
        "Turns = total requests sharing the same session_id. "
        "We do not use len(messages) because each request resends the full conversation history, "
        "making that count unreliable."
    )

# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data(start_date, end_date) -> pd.DataFrame:
    conn_str = os.environ.get("DATA_LAKE_CONN_STR", "").strip()
    if not conn_str:
        return _load_demo_data()

    container = os.environ.get("CLEAN_CONTAINER", "clean")
    try:
        client = BlobServiceClient.from_connection_string(conn_str)
        container_client = client.get_container_client(container)
        dfs = []
        current = start_date
        while current <= end_date:
            blob_path = (
                f"clean/{current.year:04d}/{current.month:02d}/{current.day:02d}/"
                f"llmaven_clean_{current.strftime('%Y-%m-%d')}.parquet"
            )
            try:
                blob = container_client.get_blob_client(blob_path)
                data = blob.download_blob().readall()
                dfs.append(pd.read_parquet(io.BytesIO(data)))
            except ResourceNotFoundError:
                pass
            current += timedelta(days=1)
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    except Exception:
        return _load_demo_data()


def _load_demo_data() -> pd.DataFrame:
    """
    Demo data that mirrors the real schema.

    Turns = total number of requests that share the same session_id.
    - sess-001 has 2 requests -> both records get turns = 2
    - sess-002 has 1 request  -> turns = 1
    - sess-003 has 1 request  -> turns = 1
    - sess-004 has 1 request  -> turns = 1
    - sess-005 has 1 request  -> turns = 1
    """
    records = [
        # sess-001: two requests (turns = 2 for both)
        {"date": pd.Timestamp("2026-03-26"), "session_id": "sess-001", "request_id": "req-001",
         "user": "researcher_01", "model": "claude-sonnet-4-6", "cost_usd": 0.00479,
         "prompt_tokens": 150, "completion_tokens": 317, "total_tokens": 467,
         "turns": 2, "source": "Claude-Code", "cache_hit": False, "duration_s": 2.1},

        {"date": pd.Timestamp("2026-03-26"), "session_id": "sess-001", "request_id": "req-002",
         "user": "researcher_01", "model": "claude-sonnet-4-6", "cost_usd": 0.00821,
         "prompt_tokens": 480, "completion_tokens": 520, "total_tokens": 1000,
         "turns": 2, "source": "Claude-Code", "cache_hit": False, "duration_s": 3.2},

        # sess-002: one request (SafeMind)
        {"date": pd.Timestamp("2026-03-26"), "session_id": "sess-002", "request_id": "req-003",
         "user": "safemind_bot", "model": "claude-sonnet-4-6", "cost_usd": 0.00210,
         "prompt_tokens": 90, "completion_tokens": 180, "total_tokens": 270,
         "turns": 1, "source": "SafeMind", "cache_hit": False, "duration_s": 1.0},

        # sess-003: one request
        {"date": pd.Timestamp("2026-03-27"), "session_id": "sess-003", "request_id": "req-004",
         "user": "researcher_02", "model": "claude-sonnet-4-6", "cost_usd": 0.01200,
         "prompt_tokens": 600, "completion_tokens": 800, "total_tokens": 1400,
         "turns": 1, "source": "Claude-Code", "cache_hit": False, "duration_s": 4.5},

        # sess-004: one request
        {"date": pd.Timestamp("2026-03-27"), "session_id": "sess-004", "request_id": "req-005",
         "user": "researcher_03", "model": "claude-sonnet-4-6", "cost_usd": 0.00350,
         "prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300,
         "turns": 1, "source": "curl", "cache_hit": False, "duration_s": 1.2},

        # sess-005: one request (cache hit)
        {"date": pd.Timestamp("2026-03-28"), "session_id": "sess-005", "request_id": "req-006",
         "user": "researcher_01", "model": "claude-sonnet-4-6", "cost_usd": 0.00980,
         "prompt_tokens": 400, "completion_tokens": 600, "total_tokens": 1000,
         "turns": 1, "source": "Claude-Code", "cache_hit": True, "duration_s": 0.1},
    ]
    return pd.DataFrame(records)


# ── Load + filter ──────────────────────────────────────────────────────────────
start, end = (date_range[0], date_range[1]) if len(date_range) == 2 else (date_range[0], date_range[0])
df_all = load_data(start, end)

if df_all.empty:
    st.warning("No data found for the selected date range.")
    st.stop()

df = df_all[df_all["source"].isin(filter_source)] if filter_source else df_all

is_demo = not os.environ.get("DATA_LAKE_CONN_STR", "").strip()
if is_demo:
    st.markdown("""
    <div class="demo-banner">
        <span>Demo mode</span> &mdash; showing sample data.
        Set <code>DATA_LAKE_CONN_STR</code> environment variable to load real LLMaven sessions.
    </div>
    """, unsafe_allow_html=True)

# ── KPI Row ────────────────────────────────────────────────────────────────────
total_sessions  = df["session_id"].nunique()
avg_turns       = df.groupby("session_id")["turns"].first().mean()
cache_rate      = df["cache_hit"].mean() * 100
cost_per_session = df["cost_usd"].sum() / total_sessions if total_sessions else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
kpis = [
    ("Total Requests",    f"{len(df):,}",                       "",           ""),
    ("Unique Sessions",   f"{total_sessions:,}",                "",           ""),
    ("Total Cost (USD)",  f"${df['cost_usd'].sum():.4f}",       "kpi-accent", ""),
    ("Total Tokens",      f"{df['total_tokens'].sum():,}",       "",           ""),
    ("Avg Turns/Session", f"{avg_turns:.1f}",                   "",           "turns = requests per session"),
    ("Cache Hit Rate",    f"{cache_rate:.0f}%",                 "",           "cached = no new Claude call"),
]
for col, (label, value, accent, sub) in zip([c1, c2, c3, c4, c5, c6], kpis):
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {accent}">{value}</div>
        {"<div class='kpi-sub'>" + sub + "</div>" if sub else ""}
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Usage Overview", "Session Analysis", "Raw Data"])

# ── TAB 1: Usage Overview ──────────────────────────────────────────────────────
with tab1:

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Model Usage</div>', unsafe_allow_html=True)
        model_counts = df["model"].value_counts().reset_index()
        model_counts.columns = ["model", "count"]
        fig = px.pie(model_counts, names="model", values="count", hole=0.58,
                     color_discrete_sequence=COLORS)
        fig.update_traces(
            textposition="inside", textinfo="percent+label",
            textfont={"color": "#ffffff", "size": 12},
            marker={"line": {"color": "#0f1117", "width": 2}}
        )
        fig.update_layout(
            **CHART_THEME, showlegend=False,
            annotations=[{"text": "Models", "x": 0.5, "y": 0.5,
                           "font_size": 13, "showarrow": False, "font_color": "#8892b0"}]
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Daily Cost (USD)</div>', unsafe_allow_html=True)
        daily_cost = df.groupby("date")["cost_usd"].sum().reset_index()
        fig = px.area(daily_cost, x="date", y="cost_usd",
                      labels={"cost_usd": "Cost (USD)", "date": ""},
                      color_discrete_sequence=["#64ffda"])
        fig.update_traces(fill="tozeroy", fillcolor="rgba(100,255,218,0.08)", line={"width": 2})
        fig.update_layout(**CHART_THEME, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Token Distribution: Input vs Output</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="insight">Input tokens dominate because each request resends the full '
            'conversation history as context. Output tokens are just the reply.</div>',
            unsafe_allow_html=True
        )
        token_data = pd.DataFrame({
            "Type":   ["Input (prompt)", "Output (completion)"],
            "Tokens": [df["prompt_tokens"].sum(), df["completion_tokens"].sum()],
        })
        fig = px.bar(token_data, x="Type", y="Tokens", color="Type",
                     color_discrete_sequence=["#7b61ff", "#64ffda"], text="Tokens")
        fig.update_traces(
            texttemplate="%{text:,}", textposition="outside",
            textfont={"color": "#ccd6f6"}, marker_line_width=0
        )
        fig.update_layout(**CHART_THEME, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Requests by Source</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="insight">Use the sidebar to filter out SafeMind and isolate coding activity.</div>',
            unsafe_allow_html=True
        )
        source_counts = df_all["source"].value_counts().reset_index()
        source_counts.columns = ["source", "count"]
        fig = px.bar(source_counts, x="source", y="count",
                     color="source", color_discrete_sequence=COLORS,
                     labels={"source": "", "count": "Requests"})
        fig.update_traces(marker_line_width=0)
        fig.update_layout(**CHART_THEME, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# ── TAB 2: Session Analysis ────────────────────────────────────────────────────
with tab2:

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Turns per Session Distribution</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="insight">'
            '<b>Turns = number of separate requests in one session.</b> '
            'We group by session_id and count records, not message list length. '
            'Most sessions are single-turn (quick one-off questions). '
            'Multi-turn sessions represent deeper work.'
            '</div>',
            unsafe_allow_html=True
        )
        # One row per session showing its total turns
        turns_per_session = df.groupby("session_id")["turns"].first().reset_index()
        fig = px.histogram(
            turns_per_session, x="turns", nbins=20,
            labels={"turns": "Total Turns in Session", "count": "Number of Sessions"},
            color_discrete_sequence=["#ff6b9d"]
        )
        fig.update_traces(marker_line_width=0)
        fig.update_layout(**CHART_THEME, bargap=0.15, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Top Users by Spend</div>', unsafe_allow_html=True)
        top_users = (
            df.groupby("user")
            .agg(total_cost=("cost_usd", "sum"), requests=("request_id", "count"))
            .sort_values("total_cost", ascending=True)
            .tail(8).reset_index()
        )
        fig = px.bar(top_users, x="total_cost", y="user", orientation="h",
                     color="total_cost", color_continuous_scale=["#2d3561", "#64ffda"],
                     labels={"total_cost": "Total Cost (USD)", "user": ""},
                     text="total_cost")
        fig.update_traces(
            texttemplate="$%{text:.4f}", textposition="outside",
            textfont={"color": "#ccd6f6"}, marker_line_width=0
        )
        fig.update_layout(**CHART_THEME, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Cost per Session</div>', unsafe_allow_html=True)
        session_cost = (
            df.groupby("session_id")
            .agg(total_cost=("cost_usd", "sum"), turns=("turns", "first"), source=("source", "first"))
            .reset_index()
        )
        fig = px.scatter(
            session_cost, x="turns", y="total_cost",
            color="source", color_discrete_sequence=COLORS,
            labels={"turns": "Turns in Session", "total_cost": "Total Cost (USD)", "source": "Source"},
            hover_data=["session_id"]
        )
        fig.update_layout(**CHART_THEME)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Response Time Distribution (seconds)</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="insight">Cache hits show near-zero response times. '
            'Non-cached requests reflect actual model latency.</div>',
            unsafe_allow_html=True
        )
        fig = px.histogram(
            df, x="duration_s", color="cache_hit",
            color_discrete_map={True: "#64ffda", False: "#7b61ff"},
            labels={"duration_s": "Duration (seconds)", "cache_hit": "Cache Hit"},
            barmode="overlay", nbins=20
        )
        fig.update_traces(marker_line_width=0, opacity=0.8)
        fig.update_layout(**CHART_THEME, bargap=0.1)
        st.plotly_chart(fig, use_container_width=True)

# ── TAB 3: Raw Data ────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">Raw Records</div>', unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Showing", f"{len(df):,} records")
    col_b.metric("Date range", f"{start} to {end}")
    col_c.metric("Sources", ", ".join(filter_source) if filter_source else "All")

    st.markdown("<br>", unsafe_allow_html=True)

    show_cols = ["date", "user", "model", "cost_usd", "prompt_tokens",
                 "completion_tokens", "turns", "source", "cache_hit", "duration_s", "session_id"]

    st.dataframe(
        df[show_cols].sort_values("date", ascending=False).reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
        column_config={
            "cost_usd":          st.column_config.NumberColumn("Cost (USD)", format="$%.5f"),
            "prompt_tokens":     st.column_config.NumberColumn("Prompt Tokens", format="%d"),
            "completion_tokens": st.column_config.NumberColumn("Completion Tokens", format="%d"),
            "duration_s":        st.column_config.NumberColumn("Duration (s)", format="%.2f"),
            "turns":             st.column_config.NumberColumn("Turns", help="Total requests in this session", format="%d"),
            "cache_hit":         st.column_config.CheckboxColumn("Cache Hit"),
            "date":              st.column_config.DateColumn("Date"),
        }
    )

    st.markdown("---")
    st.markdown("**Turns column explained**")
    st.info(
        "Turns = total number of requests sharing the same session_id. "
        "For example, if researcher_01 sent 3 separate messages in one coding session, "
        "all 3 records get turns = 3. "
        "We do not use len(proxy_server_request.messages) because each request resends "
        "the full conversation history, making the message list length grow with every turn "
        "and therefore not reflect the actual turn count."
    )
