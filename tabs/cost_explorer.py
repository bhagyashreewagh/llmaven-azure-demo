"""
tabs/cost_explorer.py
---------------------
Tab 2 - Cost Explorer
  - Cost Breakdown treemap (user -> model, click to drill in)
  - Cost Per Request by Model (box plot)
  - Monthly Burn Rate (bar)
  - What-If Calculator (Haiku savings estimate)
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from config import C, SEQ, _PL
from utils import fmt_usd, kpi, insight, sec, _style


def render(df: pd.DataFrame) -> None:
    # ---- Treemap ----
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

    # ---- Box plot + Monthly Burn Rate (side by side) ----
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(sec("Cost Per Request by Model"), unsafe_allow_html=True)
        fig_box = px.box(
            df[df["spend"] > 0], x="model", y="spend",
            color="model", color_discrete_sequence=SEQ,
            points="outliers",
        )
        fig_box.update_layout(
            **_PL, height=420, showlegend=False,
            xaxis=dict(
                title=dict(text="Model", font=dict(size=13, color=C["muted"])),
                showgrid=False, tickfont=dict(size=12, color=C["text_md"]),
            ),
            yaxis=dict(
                title=dict(text="Spend per Request (USD)", font=dict(size=13, color=C["muted"])),
                tickprefix="$", gridcolor="#E8EEFF",
                tickfont=dict(size=12, color=C["text_md"]),
            ),
        )
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
        fig_mo = px.bar(
            monthly, x="month", y="spend",
            color="month",
            color_discrete_sequence=[C["primary"], C["sail"], C["pink"]],
        )
        fig_mo.update_layout(
            **_PL, height=420, showlegend=False,
            xaxis=dict(
                title=dict(text="Month", font=dict(size=13, color=C["muted"])),
                showgrid=False, tickfont=dict(size=12, color=C["text_md"]),
            ),
            yaxis=dict(
                title=dict(text="Total Spend (USD)", font=dict(size=13, color=C["muted"])),
                tickprefix="$", gridcolor="#E8EEFF",
                tickfont=dict(size=12, color=C["text_md"]),
            ),
        )
        fig_mo.update_traces(hovertemplate="<b>%{x}</b><br>$%{y:.4f}<extra></extra>")
        _style(fig_mo)
        st.plotly_chart(fig_mo, use_container_width=True)
        st.markdown(insight(
            "Burn rate is the total dollars spent on LLM API calls per calendar month."
        ), unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="div"></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ---- What-If Calculator ----
    st.markdown(
        sec("What-If Calculator - What if everything ran on the cheapest model (Claude Haiku)?"),
        unsafe_allow_html=True,
    )
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
        f"Even migrating half of non-Haiku requests would save approx. <b>{fmt_usd(savings_wh / 2)}</b>."
    ), unsafe_allow_html=True)
