"""
LLMaven Usage Dashboard
========================
A Streamlit dashboard that reads clean Parquet files from Azure Data Lake
and shows usage analytics — replicating and extending what Carlos did manually.

Charts shown:
  1. Model usage breakdown (which AI models people use)
  2. Daily cost over time
  3. Token distribution (input vs output — Carlos's chart 2)
  4. Turns per session distribution (Carlos's chart 3)
  5. Top users by spend
  6. Source breakdown (Claude-Code vs SafeMind vs curl etc.)

Run locally:
  DATA_LAKE_CONN_STR="..." CLEAN_CONTAINER="clean" streamlit run app.py

Or with demo data (no Azure needed):
  streamlit run app.py
"""

import os
import io
import json
import logging
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LLMaven Usage Dashboard",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 LLMaven Usage Dashboard")
st.caption("AI usage analytics — powered by LiteLLM spend logs")

# ── Sidebar controls ──────────────────────────────────────────────────────────
st.sidebar.header("Filters")

date_range = st.sidebar.date_input(
    "Date range",
    value=(datetime.today() - timedelta(days=30), datetime.today()),
    max_value=datetime.today(),
)

filter_source = st.sidebar.multiselect(
    "Source (filter like Carlos did)",
    options=["Claude-Code", "SafeMind", "curl", "python-script", "unknown"],
    default=["Claude-Code", "curl", "python-script", "unknown"],
    help="Uncheck 'SafeMind' to exclude SafeMind calls — exactly what Carlos did",
)

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)   # Cache for 5 minutes — don't re-download on every interaction
def load_data(start_date, end_date) -> pd.DataFrame:
    """
    Load clean Parquet files from Azure Data Lake for the given date range.
    Falls back to demo data if no Azure connection string is configured.
    """
    conn_str = os.environ.get("DATA_LAKE_CONN_STR", "").strip()

    if not conn_str:
        st.info("No Azure connection — showing demo data. Set DATA_LAKE_CONN_STR to use real data.")
        return _load_demo_data()

    container = os.environ.get("CLEAN_CONTAINER", "clean")

    try:
        client = BlobServiceClient.from_connection_string(conn_str)
        container_client = client.get_container_client(container)

        dfs = []
        current = start_date
        while current <= end_date:
            blob_path = f"clean/{current.year:04d}/{current.month:02d}/{current.day:02d}/llmaven_clean_{current.strftime('%Y-%m-%d')}.parquet"
            try:
                blob = container_client.get_blob_client(blob_path)
                data = blob.download_blob().readall()
                df = pd.read_parquet(io.BytesIO(data))
                dfs.append(df)
            except ResourceNotFoundError:
                pass   # No data for this day — skip silently
            current += timedelta(days=1)

        if not dfs:
            st.warning("No data found for the selected date range.")
            return pd.DataFrame()

        return pd.concat(dfs, ignore_index=True)

    except Exception as e:
        st.error(f"Failed to load data from Azure: {e}")
        return _load_demo_data()


def _load_demo_data() -> pd.DataFrame:
    """Demo data matching the clean schema — same as real data format."""
    records = [
        # Session 1 — researcher using Claude Code (2 turns)
        {"date": pd.Timestamp("2026-03-26"), "session_id": "sess-001", "request_id": "req-001",
         "user": "researcher_01", "model": "claude-sonnet-4-6", "model_full": "anthropic/claude-sonnet-4-6",
         "cost_usd": 0.00479, "prompt_tokens": 150, "completion_tokens": 317, "total_tokens": 467,
         "turns": 1, "source": "Claude-Code", "cache_hit": False, "duration_s": 2.1},
        {"date": pd.Timestamp("2026-03-26"), "session_id": "sess-001", "request_id": "req-002",
         "user": "researcher_01", "model": "claude-sonnet-4-6", "model_full": "anthropic/claude-sonnet-4-6",
         "cost_usd": 0.00821, "prompt_tokens": 480, "completion_tokens": 520, "total_tokens": 1000,
         "turns": 2, "source": "Claude-Code", "cache_hit": False, "duration_s": 3.2},
        # Session 2 — SafeMind call
        {"date": pd.Timestamp("2026-03-26"), "session_id": "sess-002", "request_id": "req-003",
         "user": "safemind_bot", "model": "claude-sonnet-4-6", "model_full": "anthropic/claude-sonnet-4-6",
         "cost_usd": 0.00210, "prompt_tokens": 90, "completion_tokens": 180, "total_tokens": 270,
         "turns": 1, "source": "SafeMind", "cache_hit": False, "duration_s": 1.0},
        # Session 3 — another researcher, next day
        {"date": pd.Timestamp("2026-03-27"), "session_id": "sess-003", "request_id": "req-004",
         "user": "researcher_02", "model": "claude-sonnet-4-6", "model_full": "anthropic/claude-sonnet-4-6",
         "cost_usd": 0.01200, "prompt_tokens": 600, "completion_tokens": 800, "total_tokens": 1400,
         "turns": 3, "source": "Claude-Code", "cache_hit": False, "duration_s": 4.5},
        {"date": pd.Timestamp("2026-03-27"), "session_id": "sess-004", "request_id": "req-005",
         "user": "researcher_03", "model": "claude-sonnet-4-6", "model_full": "anthropic/claude-sonnet-4-6",
         "cost_usd": 0.00350, "prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300,
         "turns": 1, "source": "curl", "cache_hit": False, "duration_s": 1.2},
        {"date": pd.Timestamp("2026-03-28"), "session_id": "sess-005", "request_id": "req-006",
         "user": "researcher_01", "model": "claude-sonnet-4-6", "model_full": "anthropic/claude-sonnet-4-6",
         "cost_usd": 0.00980, "prompt_tokens": 400, "completion_tokens": 600, "total_tokens": 1000,
         "turns": 4, "source": "Claude-Code", "cache_hit": True, "duration_s": 0.1},
    ]
    return pd.DataFrame(records)


# ── Load + filter data ────────────────────────────────────────────────────────
start, end = (date_range[0], date_range[1]) if len(date_range) == 2 else (date_range[0], date_range[0])
df_all = load_data(start, end)

if df_all.empty:
    st.stop()

# Apply source filter (this is what Carlos did to remove SafeMind)
df = df_all[df_all["source"].isin(filter_source)] if filter_source else df_all

# ── KPI row ───────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Requests",    f"{len(df):,}")
col2.metric("Unique Sessions",   f"{df['session_id'].nunique():,}")
col3.metric("Total Cost",        f"${df['cost_usd'].sum():.4f}")
col4.metric("Total Tokens",      f"{df['total_tokens'].sum():,}")
col5.metric("Unique Users",      f"{df['user'].nunique():,}")

st.divider()

# ── Chart row 1 ───────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    # Carlos's Chart 1 — model usage
    st.subheader("Model Usage")
    model_counts = df["model"].value_counts().reset_index()
    model_counts.columns = ["model", "count"]
    fig = px.pie(
        model_counts,
        names="model",
        values="count",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    # Daily cost over time
    st.subheader("Daily Cost (USD)")
    daily_cost = df.groupby("date")["cost_usd"].sum().reset_index()
    fig = px.bar(
        daily_cost,
        x="date",
        y="cost_usd",
        labels={"cost_usd": "Cost (USD)", "date": "Date"},
        color_discrete_sequence=["#636EFA"],
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ── Chart row 2 ───────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    # Carlos's Chart 2 — token distribution (input vs output)
    st.subheader("Token Distribution (Input vs Output)")
    st.caption("The bulk should be input — all that code context sent to Claude")
    token_data = pd.DataFrame({
        "Type":   ["Input (prompt)", "Output (completion)"],
        "Tokens": [df["prompt_tokens"].sum(), df["completion_tokens"].sum()],
    })
    fig = px.bar(
        token_data,
        x="Type",
        y="Tokens",
        color="Type",
        color_discrete_sequence=["#EF553B", "#00CC96"],
        text="Tokens",
    )
    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    # Carlos's Chart 3 — turns per session
    st.subheader("Turns per Session")
    st.caption("Most are 1-turn. The longer ones are the interesting ones.")
    turns_per_session = df.groupby("session_id")["turns"].max().reset_index()
    fig = px.histogram(
        turns_per_session,
        x="turns",
        nbins=20,
        labels={"turns": "Number of Turns", "count": "Sessions"},
        color_discrete_sequence=["#AB63FA"],
    )
    fig.update_layout(bargap=0.1)
    st.plotly_chart(fig, use_container_width=True)

# ── Chart row 3 ───────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    # Source breakdown — Claude-Code vs SafeMind vs curl etc.
    st.subheader("Requests by Source")
    st.caption("Use sidebar to filter sources — e.g. uncheck SafeMind to focus on coding activity")
    source_counts = df_all["source"].value_counts().reset_index()  # use df_all to show all sources
    source_counts.columns = ["source", "count"]
    fig = px.bar(
        source_counts,
        x="source",
        y="count",
        color="source",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={"source": "Source App", "count": "Requests"},
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    # Top users by cost
    st.subheader("Top Users by Cost")
    top_users = (
        df.groupby("user")
        .agg(total_cost=("cost_usd", "sum"), requests=("request_id", "count"))
        .sort_values("total_cost", ascending=False)
        .head(10)
        .reset_index()
    )
    fig = px.bar(
        top_users,
        x="user",
        y="total_cost",
        color="requests",
        labels={"total_cost": "Total Cost (USD)", "user": "User", "requests": "# Requests"},
        color_continuous_scale="Blues",
        text="total_cost",
    )
    fig.update_traces(texttemplate="$%{text:.4f}", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

# ── Raw data table ────────────────────────────────────────────────────────────
st.divider()
st.subheader("Raw Records")
show_cols = ["date", "user", "model", "cost_usd", "prompt_tokens",
             "completion_tokens", "turns", "source", "session_id"]
st.dataframe(
    df[show_cols].sort_values("date", ascending=False),
    use_container_width=True,
    hide_index=True,
)
