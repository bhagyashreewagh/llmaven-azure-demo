"""
tabs/time_intelligence.py
-------------------------
Tab 3 - Time Intelligence
  - Spend Calendar heatmap (Jan-Mar)
  - Hour-of-Day Activity (stacked bar)
  - Day-of-Week Pattern (bar)
  - Week-over-Week Spend and Volume (dual axis)
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from config import C, SEQ, _PL
from utils import insight, sec, _style


def render(df: pd.DataFrame) -> None:
    # ---- Spend Calendar ----
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
            [0,    C["border"]],
            [0.2,  C["sail_lt"]],
            [0.55, C["sail"]],
            [0.8,  C["primary"]],
            [1,    C["primary_dk"]],
        ],
        hovertemplate="<b>%{x}</b> - %{y}<br>$%{z:.4f}<extra></extra>",
        showscale=True,
        xgap=4, ygap=4,
        colorbar=dict(thickness=12, len=0.7, tickprefix="$", outlinewidth=0),
    ))
    fig_cal.update_layout(
        **_PL, height=245,
        yaxis=dict(autorange="reversed", tickfont=dict(size=12, color=C["text_md"])),
        xaxis=dict(tickfont=dict(size=11, color=C["text_md"])),
    )
    _style(fig_cal)
    st.plotly_chart(fig_cal, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Hour-of-Day + Day-of-Week (side by side) ----
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(sec("Hour-of-Day Activity (UTC)"), unsafe_allow_html=True)
        hrly = df.groupby(["hour", "model"])["spend"].sum().reset_index()
        fig_hr = px.bar(
            hrly, x="hour", y="spend", color="model", barmode="stack",
            color_discrete_sequence=SEQ, labels={"model": ""},
        )
        fig_hr.update_layout(
            **{**_PL, "margin": dict(t=45, b=120, l=10, r=10)}, height=360,
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
            ),
        )
        _style(fig_hr)
        st.plotly_chart(fig_hr, use_container_width=True)
        peak_hr = df.groupby("hour")["spend"].sum().idxmax()
        st.markdown(insight(
            f"Peak activity is around <b>{peak_hr:02d}:00 UTC</b>. "
            "Requests outside business hours often indicate automated pipelines or overseas users."
        ), unsafe_allow_html=True)

    with c2:
        st.markdown(sec("Day-of-Week Pattern"), unsafe_allow_html=True)
        DOW_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_d = df.groupby("dow")["spend"].sum().reset_index()
        dow_d["dow"] = pd.Categorical(dow_d["dow"], categories=DOW_ORDER, ordered=True)
        dow_d = dow_d.sort_values("dow")
        fig_dow = px.bar(
            dow_d, x="dow", y="spend",
            color="dow", color_discrete_sequence=SEQ,
        )
        fig_dow.update_layout(
            **{**_PL, "margin": dict(t=45, b=120, l=10, r=10)},
            height=360, showlegend=False,
            xaxis=dict(
                showgrid=False,
                title=dict(text="Day of Week", font=dict(size=13, color=C["muted"])),
                tickfont=dict(size=12, color=C["text_md"]),
            ),
            yaxis=dict(
                tickprefix="$", gridcolor="#E8EEFF",
                title=dict(text="Spend (USD)", font=dict(size=13, color=C["muted"])),
                tickfont=dict(size=12, color=C["text_md"]),
            ),
        )
        fig_dow.update_traces(hovertemplate="<b>%{x}</b><br>$%{y:.4f}<extra></extra>")
        _style(fig_dow)
        st.plotly_chart(fig_dow, use_container_width=True)
        busiest  = dow_d.loc[dow_d["spend"].idxmax(), "dow"]
        wknd_pct = (
            dow_d[dow_d["dow"].isin(["Saturday", "Sunday"])]["spend"].sum()
            / dow_d["spend"].sum() * 100
        )
        st.markdown(insight(
            f"<b>{busiest}</b> is the busiest day. "
            f"Weekend activity is <b>{wknd_pct:.0f}%</b> of total, "
            f"{'suggesting mostly automated use' if wknd_pct > 20 else 'pointing to human / business-hours usage'}."
        ), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Week-over-Week ----
    st.markdown(sec("Week-over-Week Spend and Volume"), unsafe_allow_html=True)

    df["_wk"] = df["start_dt"].dt.isocalendar().week.astype(int)
    wkly = df.groupby("_wk").agg(
        spend=("spend", "sum"),
        requests=("request_id", "count"),
    ).reset_index(names="week_num")

    fig_wk = make_subplots(specs=[[{"secondary_y": True}]])
    fig_wk.add_trace(
        go.Bar(x=wkly["week_num"], y=wkly["spend"],
               name="Spend", marker_color=C["sail_lt"],
               hovertemplate="Week %{x}<br>$%{y:.4f}<extra></extra>"),
        secondary_y=False,
    )
    fig_wk.add_trace(
        go.Scatter(x=wkly["week_num"], y=wkly["requests"],
                   name="Requests", line=dict(color=C["pink"], width=2.5),
                   hovertemplate="Week %{x}<br>%{y:,} requests<extra></extra>"),
        secondary_y=True,
    )
    fig_wk.update_layout(
        **{**_PL, "margin": dict(t=45, b=80, l=10, r=10)}, height=320,
        legend=dict(orientation="h", y=-0.28, x=0.5, xanchor="center",
                    font=dict(size=14, color=C["text"]), bgcolor="rgba(0,0,0,0)"),
    )
    fig_wk.update_yaxes(
        tickprefix="$", gridcolor="#E8EEFF",
        title_text="Weekly Spend (USD)",
        title_font=dict(size=13, color=C["muted"]),
        tickfont=dict(size=12, color=C["text_md"]),
        secondary_y=False,
    )
    fig_wk.update_yaxes(
        showgrid=False,
        title_text="Number of Requests",
        title_font=dict(size=13, color=C["muted"]),
        tickfont=dict(size=12, color=C["text_md"]),
        secondary_y=True,
    )
    fig_wk.update_xaxes(
        title_text="Week Number",
        title_font=dict(size=13, color=C["muted"]),
        tickfont=dict(size=12, color=C["text_md"]),
        showgrid=False,
    )
    _style(fig_wk)
    st.plotly_chart(fig_wk, use_container_width=True)
