"""
data.py
-------
Data loading and preprocessing.

load_data() reads the JSONL log files from the ZIP archive specified
by config.ZIP_PATH and returns a clean pandas DataFrame.

The ZIP file is expected to contain one or more *.jsonl files, each
holding one LiteLLM proxy log record per line (JSON format).
"""

import zipfile
import json
import pandas as pd
import streamlit as st
from config import ZIP_PATH


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _clean_model(raw: str) -> str:
    """Normalise raw LiteLLM model strings into display-friendly names."""
    r = raw.lower()
    if "haiku"  in r:                    return "Claude Haiku"
    if "sonnet" in r and "bedrock" in r: return "Claude Sonnet (Bedrock)"
    if "sonnet" in r:                    return "Claude Sonnet"
    if "gpt"    in r or "openai" in r:   return "OpenAI (GPT)"
    if "opus"   in r:                    return "Claude Opus"
    return "Other"


def _cache_savings(row) -> float:
    """
    Estimate dollars saved by serving tokens from cache instead of
    billing them at standard input rates.

    Rates used (per 1M tokens):
      Claude Haiku  : $0.80 standard  vs $0.08 cached  -> $0.72 saved / 1M
      All others    : $3.00 standard  vs $0.30 cached  -> $2.70 saved / 1M
    """
    t = row["cache_read"]
    if t <= 0:
        return 0.0
    rate = (0.80 - 0.08) if "haiku" in row["model_raw"].lower() else (3.00 - 0.30)
    return t * rate / 1_000_000


# ---------------------------------------------------------------------------
# Public: cached loader
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Parsing 3 months of API call logs...")
def load_data() -> pd.DataFrame:
    """
    Parse every *.jsonl file inside the ZIP archive and return a tidy DataFrame.

    Columns returned
    ----------------
    request_id, spend, model_raw, model, status, start_dt, end_dt,
    date, hour, dow, month, latency, total_tokens, prompt_tokens,
    completion_tokens, cache_read, cache_create, reasoning_tokens,
    session_id, user, team, cache_savings, spend_haiku
    """
    rows = []
    with zipfile.ZipFile(ZIP_PATH) as zf:
        for name in sorted(zf.namelist()):
            if not name.endswith(".jsonl"):
                continue
            with zf.open(name) as f:
                for raw_line in f:
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    try:
                        r   = json.loads(raw_line)
                        m   = r.get("metadata") or {}
                        u   = m.get("usage_object") or {}
                        ptd = u.get("prompt_tokens_details") or {}
                        ctd = u.get("completion_tokens_details") or {}
                        rows.append({
                            "request_id":        r.get("request_id", ""),
                            "spend":             float(r.get("spend") or 0),
                            "model_raw":         str(r.get("model") or ""),
                            "status":            r.get("status", "unknown"),
                            "start_time":        r.get("startTime"),
                            "end_time":          r.get("endTime"),
                            "total_tokens":      int(r.get("total_tokens") or 0),
                            "prompt_tokens":     int(r.get("prompt_tokens") or 0),
                            "completion_tokens": int(r.get("completion_tokens") or 0),
                            "session_id":        r.get("session_id", ""),
                            "user":              m.get("user_api_key_alias") or "unknown",
                            "team":              m.get("user_api_key_team_alias") or "No Team",
                            "cache_read":        int(
                                u.get("cache_read_input_tokens")
                                or ptd.get("cached_tokens") or 0
                            ),
                            "cache_create":      int(
                                u.get("cache_creation_input_tokens")
                                or ptd.get("cache_creation_tokens") or 0
                            ),
                            "reasoning_tokens":  int(ctd.get("reasoning_tokens") or 0),
                        })
                    except Exception:
                        continue

    df = pd.DataFrame(rows)
    df["start_dt"] = pd.to_datetime(df["start_time"], utc=True, errors="coerce")
    df["end_dt"]   = pd.to_datetime(df["end_time"],   utc=True, errors="coerce")
    df = df.dropna(subset=["start_dt"])
    df["date"]    = df["start_dt"].dt.date
    df["hour"]    = df["start_dt"].dt.hour
    df["dow"]     = df["start_dt"].dt.day_name()
    df["month"]   = df["start_dt"].dt.month_name()
    df["latency"] = (df["end_dt"] - df["start_dt"]).dt.total_seconds().clip(0, 300)
    df["model"]   = df["model_raw"].apply(_clean_model)
    df["cache_savings"] = df.apply(_cache_savings, axis=1)

    # What-if: cost if every request had used Claude Haiku
    HAIKU_IN, HAIKU_OUT = 0.80 / 1_000_000, 4.00 / 1_000_000
    df["spend_haiku"] = df["prompt_tokens"] * HAIKU_IN + df["completion_tokens"] * HAIKU_OUT

    return df
