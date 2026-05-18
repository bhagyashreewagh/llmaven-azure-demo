"""
tabs/ask_the_data.py
--------------------
Tab 7 - Ask the Data
  - Plain-English Q&A powered by the Anthropic API (claude-sonnet-4-6)
  - Example chip buttons that pre-fill the question box
  - Inline 3-dot bounce animation while waiting for the answer
  - API key must be set via ANTHROPIC_API_KEY env var (or .env file)
"""

import json
import os

import anthropic
import streamlit as st

from config import C
from styles import SVG_AI_BOT
from utils import insight, md_to_html

EXAMPLE_QS = [
    "Who spent the most overall?",
    "Which model is best value?",
    "Any spending spikes?",
    "Cache hit rate trend?",
    "Busiest day of week?",
    "Who is most efficient?",
]


def render(df) -> None:
    # ---- Header ----
    ask_c1, ask_c2 = st.columns([3, 1])
    with ask_c1:
        st.markdown(f"""
        <div class="ai-header">
          <div style='font-size:1.45rem;font-weight:800;color:{C["text"]};letter-spacing:-0.01em'>
            Ask Anything About Your Data
          </div>
          <div style='color:{C["muted"]};font-size:0.9rem;margin-top:0.35rem;line-height:1.65'>
            Type a question in plain English. No SQL, no code needed.
            The AI reads your <b style='color:{C["primary"]}'>{len(df):,} filtered requests</b>
            and answers directly. Use the sidebar to narrow the data first.
          </div>
        </div>
        """, unsafe_allow_html=True)
    with ask_c2:
        st.markdown(
            f"<div style='text-align:center;opacity:0.9;padding-top:0.3rem'>{SVG_AI_BOT}</div>",
            unsafe_allow_html=True,
        )

    # ---- Example chips ----
    st.markdown(
        f"<div style='font-size:0.82rem;color:{C['muted']};margin-bottom:0.5rem;font-weight:500'>Try one of these:</div>",
        unsafe_allow_html=True,
    )

    # Pop chip question set by a previous run before rendering the text input
    chip_q = st.session_state.pop("_chip_question", None)

    chip_cols = st.columns(len(EXAMPLE_QS))
    for col, q in zip(chip_cols, EXAMPLE_QS):
        if col.button(q, key=f"q_{q[:14]}", use_container_width=True):
            st.session_state["_chip_question"] = q
            st.rerun()

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
    user_q = st.text_input(
        "Question",
        value=chip_q or "",
        placeholder='e.g. "Which user had the biggest January spike and why might that be?"',
        label_visibility="collapsed",
    )

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    ask_btn = st.button("Analyze", type="primary")
    run_q   = chip_q or (user_q if ask_btn else None)

    if run_q:
        if not api_key:
            st.warning(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file or export it in your shell, then restart the app."
            )
        else:
            # Build a stats summary to pass to the model
            summary = {
                "period":            f"{df['date'].min()} to {df['date'].max()}",
                "total_requests":    len(df),
                "total_spend_usd":   round(df["spend"].sum(), 6),
                "users":             df["user"].unique().tolist(),
                "spend_by_user":     df.groupby("user")["spend"].sum().round(6).to_dict(),
                "requests_by_user":  df.groupby("user").size().to_dict(),
                "spend_by_model":    df.groupby("model")["spend"].sum().round(6).to_dict(),
                "spend_by_month":    df.groupby("month")["spend"].sum().round(6).to_dict(),
                "daily_spend_top20": {
                    str(k): round(v, 6)
                    for k, v in df.groupby("date")["spend"].sum()
                    .sort_values(ascending=False).head(20).items()
                },
                "total_tokens":      int(df["total_tokens"].sum()),
                "cache_read_tokens": int(df["cache_read"].sum()),
                "cache_savings_usd": round(df["cache_savings"].sum(), 6),
                "cache_pct_by_user": (
                    (df.groupby("user")["cache_read"].sum()
                     / df.groupby("user")["prompt_tokens"].sum() * 100).round(1).to_dict()
                ),
                "avg_latency_s":     round(df["latency"].mean(), 2),
                "failure_rate_pct":  round((df["status"] == "failure").mean() * 100, 2),
                "requests_by_dow":   df.groupby("dow").size().to_dict(),
                "requests_by_hour":  df.groupby("hour").size().to_dict(),
                "sessions":          int(df["session_id"].nunique()),
                "reasoning_tokens":  int(df["reasoning_tokens"].sum()),
            }

            answer_slot = st.empty()
            # Show inline bounce animation while waiting
            answer_slot.markdown(f"""
            <div class="ai-answer" style="min-height:90px;display:flex;align-items:center;justify-content:center">
              <div style="display:flex;gap:8px;align-items:center">
                <span style="width:10px;height:10px;border-radius:50%;background:{C['primary']};
                             display:inline-block;animation:bounce 1.2s ease-in-out infinite"></span>
                <span style="width:10px;height:10px;border-radius:50%;background:{C['sail']};
                             display:inline-block;animation:bounce 1.2s ease-in-out 0.2s infinite"></span>
                <span style="width:10px;height:10px;border-radius:50%;background:{C['pink']};
                             display:inline-block;animation:bounce 1.2s ease-in-out 0.4s infinite"></span>
              </div>
            </div>
            <style>
              @keyframes bounce {{
                0%,80%,100% {{ transform:translateY(0); opacity:0.5 }}
                40% {{ transform:translateY(-10px); opacity:1 }}
              }}
            </style>
            """, unsafe_allow_html=True)

            try:
                client = anthropic.Anthropic(api_key=api_key)
                resp = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=600,
                    system=(
                        "You are a sharp analytics assistant for an LLM usage dashboard. "
                        "Answer questions about the data directly and concisely. "
                        "Use **bold** for key numbers and names. "
                        "Be specific and cite actual numbers. "
                        "Keep answers under 180 words. No bullet lists, flowing prose only."
                    ),
                    messages=[{
                        "role": "user",
                        "content": (
                            "Here is a statistical summary of the LLM usage data (already filtered):\n"
                            f"```json\n{json.dumps(summary, indent=2, default=str)}\n```\n\n"
                            f"Answer this question: {run_q}"
                        ),
                    }],
                )
                answer      = resp.content[0].text
                answer_html = md_to_html(answer).replace("\n", "<br>")
                answer_slot.markdown(f"""
                <div class="ai-answer">
                  <div class="ai-lbl">AI Analysis | {len(df):,} requests | filtered view</div>
                  {answer_html}
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                answer_slot.error(f"API error: {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(insight(
        "<b>Tip:</b> Use the sidebar to filter down to one user or model, "
        "then ask what is unusual about this user for laser-focused insights."
    ), unsafe_allow_html=True)
