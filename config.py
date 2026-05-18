"""
config.py
---------
Shared constants: color palette, Plotly layout defaults, and data path.

To point the dashboard at your own data, either:
  - Set the DATA_ZIP environment variable in your .env file, or
  - Pass the path directly: DATA_ZIP=/path/to/your/logs.zip streamlit run app.py
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Data path - reads from environment; falls back to a sensible default.
# ---------------------------------------------------------------------------
ZIP_PATH = Path(os.getenv("DATA_ZIP", "data/logs.zip"))

# ---------------------------------------------------------------------------
# Skydash-inspired color palette (violet-blue + sail blue + pink on white)
# ---------------------------------------------------------------------------
C = {
    "bg":         "#F4F7FF",
    "card":       "#FFFFFF",
    "sidebar":    "#1B2942",
    "primary":    "#6571FF",
    "primary_dk": "#4D59E8",
    "sail":       "#7DA0FA",
    "sail_lt":    "#B8CCFF",
    "pink":       "#FC84A9",
    "pink_lt":    "#FDB8CD",
    "text":       "#2B2B2B",
    "text_md":    "#4A4A68",
    "muted":      "#7987A1",
    "border":     "#E8EEFF",
    "success":    "#00C9A7",
    "danger":     "#FC5A5A",
}

# Ordered sequence of accent colors for multi-series charts
SEQ = [
    "#6571FF", "#FC84A9", "#7DA0FA", "#4D59E8",
    "#FDB8CD", "#B8CCFF", "#3848D0", "#F97FAB",
    "#5A8CF8", "#9BA6FF",
]

# ---------------------------------------------------------------------------
# Shared Plotly layout defaults
# Apply with: fig.update_layout(**_PL, ...)
# ---------------------------------------------------------------------------
_PL = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#FFFFFF",
    font=dict(color="#2B2B2B", family="Poppins, sans-serif", size=14),
    margin=dict(t=45, b=30, l=10, r=10),
    hoverlabel=dict(bgcolor="#6571FF", font_color="white", font_size=14),
    uniformtext=dict(minsize=9, mode="hide"),
)
