"""
utils.py
--------
Small helper functions shared across all tab modules:
  - fmt_usd / fmt_k   : number formatters
  - kpi / insight / sec : HTML component builders
  - md_to_html         : lightweight markdown -> HTML converter
  - _style             : apply consistent axis colours to any Plotly figure
"""

import re
import plotly.graph_objects as go
from config import C


# ---------------------------------------------------------------------------
# Number formatters
# ---------------------------------------------------------------------------

def fmt_usd(v: float) -> str:
    """Format a dollar amount, e.g. $0.0042 or $12.34."""
    return f"${v:,.4f}" if v < 1 else f"${v:,.2f}"


def fmt_k(v: float) -> str:
    """Format a large integer with K/M suffix, e.g. 1.2M or 45.6K."""
    if v >= 1_000_000:
        return f"{v / 1e6:.2f}M"
    if v >= 1_000:
        return f"{v / 1e3:.1f}K"
    return f"{int(v):,}"


# ---------------------------------------------------------------------------
# HTML component builders
# ---------------------------------------------------------------------------

def kpi(label: str, value: str, note: str = "", note_cls: str = "") -> str:
    """Return an HTML string for a KPI card."""
    note_html = f"<div class='kpi-note {note_cls}'>{note}</div>" if note else ""
    return (
        f"<div class='kpi'>"
        f"<div class='kpi-lbl'>{label}</div>"
        f"<div class='kpi-val'>{value}</div>"
        f"{note_html}</div>"
    )


def insight(text: str) -> str:
    """Return an HTML string for a highlighted insight callout."""
    return f"<div class='insight'>{text}</div>"


def sec(text: str) -> str:
    """Return an HTML string for a section heading with decorative dot."""
    return f"<div class='sec'><span class='sec-dot'></span>{text}</div>"


def md_to_html(text: str) -> str:
    """Convert **bold** markdown to <b>bold</b> HTML."""
    return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)


# ---------------------------------------------------------------------------
# Plotly style helper
# ---------------------------------------------------------------------------

def _style(
    fig: go.Figure,
    height: int = None,
    legend: str = None,
    margin_b: int = None,
) -> go.Figure:
    """
    Apply consistent axis colours and optional legend / height to any Plotly figure.

    Parameters
    ----------
    fig      : the Plotly figure to modify in-place (also returned)
    height   : pixel height override
    legend   : "below" to move legend under the chart, "none" to hide it
    margin_b : explicit bottom margin in pixels
    """
    if height:
        fig.update_layout(height=height)
    if margin_b is not None:
        fig.update_layout(margin=dict(t=45, b=margin_b, l=10, r=10))
    if legend == "below":
        fig.update_layout(margin=dict(t=45, b=80, l=10, r=10))
        fig.update_layout(legend=dict(
            orientation="h", y=-0.28, x=0.5, xanchor="center",
            font=dict(size=14, color=C["text"]), bgcolor="rgba(0,0,0,0)",
        ))
    elif legend == "none":
        fig.update_layout(showlegend=False)

    # Always enforce visible axis colours
    fig.update_xaxes(
        title_font=dict(size=15, color=C["muted"]),
        tickfont=dict(size=13, color=C["text_md"]),
        zeroline=False,
    )
    fig.update_yaxes(
        title_font=dict(size=15, color=C["muted"]),
        tickfont=dict(size=13, color=C["text_md"]),
        zeroline=False,
        rangemode="tozero",
    )
    return fig
