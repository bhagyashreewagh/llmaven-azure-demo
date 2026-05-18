"""
tabs/users.py
-------------
Tab 4 - Users
  - Field definitions for leaderboard columns
  - User Leaderboard (sorted by spend, with efficiency score)
  - User Deep Dive: Daily Spend / Model Mix / Token Mix for selected user
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import C, SEQ, _PL
from utils import fmt_usd, fmt_k, kpi, insight, sec, _style


def render(df: pd.DataFrame) -> None:
    # ---- Field definitions ----
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

    # ---- Aggregate per user ----
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
        mc.markdown(
            f"<div style='padding-top:0.5rem'><span class='rank {rc}'>{rl}</span></div>",
            unsafe_allow_html=True,
        )
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

    # ---- User Deep Dive ----
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(sec("User Deep Dive"), unsafe_allow_html=True)
    sel_user = st.selectbox("Select a user", sorted(df["user"].unique()), label_visibility="collapsed")
    udf = df[df["user"] == sel_user]

    uc1, uc2, uc3 = st.columns(3)

    with uc1:
        st.markdown(sec("Daily Spend"), unsafe_allow_html=True)
        ud = udf.groupby("date")["spend"].sum().reset_index()
        ud["date"] = pd.to_datetime(ud["date"])
        fig_u1 = px.area(ud, x="date", y="spend", color_discrete_sequence=[C["primary"]])
        fig_u1.update_traces(fillcolor="rgba(101,113,255,0.12)")
        fig_u1.update_layout(
            **_PL, height=235,
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
            ),
        )
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
        fig_u2.update_layout(
            **{**_PL, "margin": dict(t=45, b=70, l=10, r=10)},
            height=270, showlegend=True,
            legend=dict(
                orientation="h", y=-0.25, x=0.5, xanchor="center",
                font=dict(size=14, color=C["text"]), bgcolor="rgba(0,0,0,0)",
            ),
        )
        st.plotly_chart(fig_u2, use_container_width=True)

    with uc3:
        st.markdown(sec("Token Mix"), unsafe_allow_html=True)
        tok = pd.DataFrame({
            "type":   ["Prompt", "Completion", "Cache Read", "Cache Create"],
            "tokens": [
                udf["prompt_tokens"].sum(), udf["completion_tokens"].sum(),
                udf["cache_read"].sum(),     udf["cache_create"].sum(),
            ],
        })
        tok = tok[tok["tokens"] > 0]
        fig_u3 = px.bar(
            tok, x="type", y="tokens", color="type",
            color_discrete_sequence=[C["primary"], C["pink"], C["sail"], C["sail_lt"]],
            text=tok["tokens"].apply(fmt_k),
        )
        fig_u3.update_traces(textposition="outside", textfont=dict(size=11, color=C["text_md"]))
        fig_u3.update_layout(
            **_PL, height=280, showlegend=False,
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
            ),
        )
        _style(fig_u3)
        st.plotly_chart(fig_u3, use_container_width=True)

    # Insight for selected user
    u_row       = us[us["user"] == sel_user].iloc[0]
    cache_pct_u = (
        udf["cache_read"].sum() / udf["prompt_tokens"].sum() * 100
        if udf["prompt_tokens"].sum() > 0 else 0
    )
    st.markdown(insight(
        f"<b>{sel_user}</b> spent <b>{fmt_usd(u_row['spend'])}</b> across "
        f"<b>{int(u_row['requests']):,}</b> requests. "
        f"Cache hit rate: <b>{cache_pct_u:.1f}%</b>. "
        f"Failure rate: <b>{u_row['failure_rate']:.1f}%</b>. "
        f"Average response time: <b>{u_row['avg_latency']:.1f}s</b>."
    ), unsafe_allow_html=True)
