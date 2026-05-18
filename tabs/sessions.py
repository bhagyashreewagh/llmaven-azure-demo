"""
tabs/sessions.py
----------------
Tab 6 - Sessions
  - 4 session KPIs (count, avg turns, avg cost, avg duration)
  - Turns per Session histogram
  - Cost vs. Session Length scatter (bubble = tokens)
  - Response Latency Distribution histogram
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from config import C, SEQ, _PL
from utils import fmt_usd, kpi, insight, sec, _style


def render(df: pd.DataFrame) -> None:
    sdf = df[df["session_id"].notna() & (df["session_id"] != "")].copy()

    if sdf.empty:
        st.info("No session data available in the current filter.")
        return

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

    # ---- KPI row ----
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(kpi("Sessions",        f"{len(ss):,}",                        "unique session IDs"),       unsafe_allow_html=True)
    k2.markdown(kpi("Avg Turns",        f"{ss['turns'].mean():.1f}",           f"max {ss['turns'].max()}"), unsafe_allow_html=True)
    k3.markdown(kpi("Avg Session Cost", fmt_usd(ss["spend"].mean()),            f"median {fmt_usd(ss['spend'].median())}"), unsafe_allow_html=True)
    k4.markdown(kpi("Avg Duration",     f"{ss['duration_min'].mean():.1f} min", f"max {ss['duration_min'].max():.0f} min"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(sec("Turns per Session"), unsafe_allow_html=True)
        fig_s1 = px.histogram(ss, x="turns", nbins=25, color_discrete_sequence=[C["primary"]])
        fig_s1.update_layout(
            **_PL,
            xaxis=dict(
                title=dict(text="Turns per Session", font=dict(size=13, color=C["muted"])),
                showgrid=False, tickfont=dict(size=12, color=C["text_md"]),
            ),
            yaxis=dict(
                title=dict(text="Number of Sessions", font=dict(size=13, color=C["muted"])),
                gridcolor="#E8EEFF", tickfont=dict(size=12, color=C["text_md"]),
            ),
        )
        _style(fig_s1, height=280, legend="none")
        st.plotly_chart(fig_s1, use_container_width=True)

    with c2:
        st.markdown(sec("Cost vs. Session Length (bubble = tokens)"), unsafe_allow_html=True)
        fig_s2 = px.scatter(
            ss[ss["spend"] > 0],
            x="turns", y="spend",
            color="user", size="total_tokens", size_max=30,
            color_discrete_sequence=SEQ,
            hover_data={"session_id": True, "user": True, "turns": True},
        )
        fig_s2.update_layout(
            **_PL,
            xaxis=dict(
                title=dict(text="Turns", font=dict(size=13, color=C["muted"])),
                showgrid=False, tickfont=dict(size=12, color=C["text_md"]),
            ),
            yaxis=dict(
                title=dict(text="Spend (USD)", font=dict(size=13, color=C["muted"])),
                tickprefix="$", gridcolor="#E8EEFF",
                tickfont=dict(size=12, color=C["text_md"]),
            ),
        )
        _style(fig_s2, height=280, legend="below")
        st.plotly_chart(fig_s2, use_container_width=True)

    # ---- Latency distribution ----
    st.markdown(sec("Response Latency Distribution"), unsafe_allow_html=True)
    lat = df[df["latency"] > 0]
    fig_lat = px.histogram(
        lat, x="latency", color="model", nbins=50,
        barmode="overlay", opacity=0.75,
        color_discrete_sequence=SEQ,
    )
    fig_lat.update_layout(
        **_PL,
        xaxis=dict(
            title=dict(text="Latency (seconds)", font=dict(size=13, color=C["muted"])),
            showgrid=False, tickfont=dict(size=12, color=C["text_md"]),
        ),
        yaxis=dict(
            title=dict(text="Count", font=dict(size=13, color=C["muted"])),
            gridcolor="#E8EEFF", tickfont=dict(size=12, color=C["text_md"]),
        ),
    )
    _style(fig_lat, height=300, legend="below")
    st.plotly_chart(fig_lat, use_container_width=True)

    p50 = lat["latency"].quantile(0.5)
    p95 = lat["latency"].quantile(0.95)
    p99 = lat["latency"].quantile(0.99)
    st.markdown(insight(
        f"Median response: <b>{p50:.1f}s</b>, P95: <b>{p95:.1f}s</b>, P99: <b>{p99:.1f}s</b>. "
        "Long tails typically indicate large context windows or extended-thinking requests."
    ), unsafe_allow_html=True)
