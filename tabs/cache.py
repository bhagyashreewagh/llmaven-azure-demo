"""
tabs/cache.py
-------------
Tab 5 - Cache
  - Savings banner (total cache savings, hit rate, tokens created)
  - Cache Read Tokens vs. Cache % daily (dual-axis)
  - Cache Efficiency by User (horizontal bar)
  - Extended Thinking reasoning tokens chart (shown only if data exists)
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from config import C, _PL
from styles import SVG_CACHE
from utils import fmt_usd, fmt_k, insight, sec, _style


def render(df: pd.DataFrame) -> None:
    tc_read   = df["cache_read"].sum()
    tc_create = df["cache_create"].sum()
    tc_save   = df["cache_savings"].sum()
    tc_pct    = tc_read / df["prompt_tokens"].sum() * 100 if df["prompt_tokens"].sum() > 0 else 0

    # ---- Savings banner ----
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

    # ---- Daily cache read vs cache % ----
    st.markdown(sec("Cache Read Tokens vs. Cache % (daily)"), unsafe_allow_html=True)
    dc = df.groupby("date").agg(
        cache_read=("cache_read", "sum"),
        prompt=("prompt_tokens", "sum"),
    ).reset_index()
    dc["date"]      = pd.to_datetime(dc["date"])
    dc["cache_pct"] = dc["cache_read"] / dc["prompt"].clip(1) * 100

    fig_c1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig_c1.add_trace(
        go.Bar(x=dc["date"], y=dc["cache_read"],
               name="Cached Tokens", marker_color=C["sail_lt"],
               hovertemplate="%{x|%b %d}<br>%{y:,.0f} tokens<extra></extra>"),
        secondary_y=False,
    )
    fig_c1.add_trace(
        go.Scatter(x=dc["date"], y=dc["cache_pct"],
                   name="Cache %", line=dict(color=C["pink"], width=2.5),
                   hovertemplate="%{x|%b %d}<br>%{y:.1f}%<extra></extra>"),
        secondary_y=True,
    )
    fig_c1.update_layout(**_PL)
    fig_c1.update_yaxes(gridcolor="#E8EEFF", title_text="Cached Tokens", zeroline=False, secondary_y=False)
    fig_c1.update_yaxes(ticksuffix="%", showgrid=False, title_text="Cache Hit %", zeroline=False, secondary_y=True)
    fig_c1.update_xaxes(showline=False, zeroline=False, tickformat="%b %d")
    _style(fig_c1, height=320, legend="below")
    st.plotly_chart(fig_c1, use_container_width=True)

    # ---- Cache efficiency by user ----
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
    fig_c2.update_layout(
        **_PL,
        xaxis=dict(
            ticksuffix="%", range=[0, 115], showgrid=False,
            title=dict(text="Cache Hit Rate", font=dict(size=13, color=C["muted"])),
            tickfont=dict(size=12, color=C["text_md"]),
        ),
        yaxis=dict(
            showgrid=False,
            title=dict(text="User", font=dict(size=13, color=C["muted"])),
            tickfont=dict(size=12, color=C["text_md"]),
        ),
    )
    _style(fig_c2, height=max(320, n_uc * 42), legend="none")
    st.plotly_chart(fig_c2, use_container_width=True)

    best  = uc.loc[uc["cache_pct"].idxmax()]
    worst = uc.loc[uc["cache_pct"].idxmin()]
    st.markdown(insight(
        f"<b>{best['user']}</b> has the highest cache utilization at <b>{best['cache_pct']:.0f}%</b>, "
        f"saving <b>{fmt_usd(best['savings'])}</b>. "
        f"<b>{worst['user']}</b> caches only <b>{worst['cache_pct']:.0f}%</b> of prompt tokens. "
        "Enabling session-based caching could significantly cut their costs."
    ), unsafe_allow_html=True)

    # ---- Reasoning tokens (conditional) ----
    if df["reasoning_tokens"].sum() > 0:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(sec("Extended Thinking - Reasoning Tokens"), unsafe_allow_html=True)
        rt = df[df["reasoning_tokens"] > 0].groupby("date")["reasoning_tokens"].sum().reset_index()
        rt["date"] = pd.to_datetime(rt["date"])
        fig_rt = px.bar(rt, x="date", y="reasoning_tokens", color_discrete_sequence=[C["primary_dk"]])
        fig_rt.update_layout(
            **_PL,
            xaxis=dict(
                showgrid=False,
                title=dict(text="Date", font=dict(size=13, color=C["muted"])),
                tickformat="%b %d",
                tickfont=dict(size=12, color=C["text_md"]),
            ),
            yaxis=dict(
                gridcolor="#E8EEFF",
                title=dict(text="Reasoning Tokens", font=dict(size=13, color=C["muted"])),
                tickfont=dict(size=12, color=C["text_md"]),
            ),
        )
        _style(fig_rt, height=220, legend="none")
        st.plotly_chart(fig_rt, use_container_width=True)
