"""
tabs/overview.py
----------------
Tab 1 - Overview
  - 5 KPI cards (spend, requests, users, tokens, cache savings)
  - Daily Spend Trend (area + 7-day rolling avg)
  - Spend by Model (donut)
  - Daily Requests by Status (stacked bar)
  - Spend by User (horizontal bar)
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import C, SEQ, _PL
from utils import fmt_usd, fmt_k, kpi, insight, sec, _style


def render(df: pd.DataFrame) -> None:
    total_spend    = df["spend"].sum()
    total_requests = len(df)
    unique_users   = df["user"].nunique()
    total_tokens   = df["total_tokens"].sum()
    total_savings  = df["cache_savings"].sum()
    failures       = (df["status"] == "failure").sum()

    # ---- KPI row ----
    k1, k2, k3, k4, k5 = st.columns(5)
    fail_pct = failures / total_requests * 100 if total_requests else 0
    k1.markdown(kpi("Total Spend",   fmt_usd(total_spend),  f"across {total_requests:,} API calls"), unsafe_allow_html=True)
    k2.markdown(kpi("API Requests",  f"{total_requests:,}", f"{failures:,} errors &nbsp;({fail_pct:.1f}%)", "warn" if failures > 0 else ""), unsafe_allow_html=True)
    k3.markdown(kpi("Active Users",  str(unique_users),     "distinct API key holders"), unsafe_allow_html=True)
    k4.markdown(kpi("Tokens Used",   fmt_k(total_tokens),   "prompt + completion + cached"), unsafe_allow_html=True)
    k5.markdown(kpi("Cache Savings", fmt_usd(total_savings), "vs. billing all tokens at standard rates", "good"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Daily Spend Trend ----
    st.markdown(sec("Daily Spend Trend"), unsafe_allow_html=True)
    daily = df.groupby("date")["spend"].sum().reset_index()
    daily["date"]   = pd.to_datetime(daily["date"])
    daily["7d_avg"] = daily["spend"].rolling(7, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["date"], y=[0] * len(daily),
        line=dict(width=0), showlegend=False, hoverinfo="skip", name="_base",
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
            showgrid=False, tickformat="%b %d",
            tickfont=dict(size=12, color=C["text_md"]),
        ),
        yaxis=dict(
            title=dict(text="Daily Spend (USD)", font=dict(size=13, color=C["muted"])),
            tickprefix="$", gridcolor="#E8EEFF",
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

    # ---- Spend by Model ----
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
                orientation="h", y=-0.22, x=0.5, xanchor="center",
                font=dict(size=14, color=C["text"]), bgcolor="rgba(0,0,0,0)",
            ),
            annotations=[dict(
                text=f"<b>{len(main)}</b><br><span style='font-size:11px'>models</span>",
                x=0.5, y=0.5, font_size=14, showarrow=False, font_color=C["primary"],
            )],
        )
        _style(fig2)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Daily Requests by Status ----
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
    fig3.update_layout(
        **{**_PL, "margin": dict(t=45, b=100, l=10, r=10)},
        height=340, barmode="stack",
        legend=dict(orientation="h", y=-0.38, x=0.5, xanchor="center",
                    font=dict(size=14, color=C["text"]), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(
            title=dict(text="Date", font=dict(size=13, color=C["muted"])),
            showgrid=False, tickformat="%b %d",
            tickfont=dict(size=12, color=C["text_md"]),
        ),
        yaxis=dict(
            title=dict(text="Number of Requests", font=dict(size=13, color=C["muted"])),
            gridcolor="#E8EEFF", tickfont=dict(size=12, color=C["text_md"]),
        ),
    )
    _style(fig3)
    st.plotly_chart(fig3, use_container_width=True)

    # ---- Spend by User ----
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
    fig4.update_layout(
        **_PL, height=bar_height,
        xaxis=dict(
            title=dict(text="Total Spend (USD)", font=dict(size=13, color=C["muted"])),
            tickprefix="$", showgrid=False,
            tickfont=dict(size=12, color=C["text_md"]),
        ),
        yaxis=dict(
            title=dict(text="User", font=dict(size=13, color=C["muted"])),
            showgrid=False, tickfont=dict(size=12, color=C["text_md"]),
        ),
    )
    _style(fig4)
    st.plotly_chart(fig4, use_container_width=True)
