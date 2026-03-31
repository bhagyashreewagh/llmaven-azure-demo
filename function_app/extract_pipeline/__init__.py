"""
Azure Function — LLMaven Extract Pipeline
==========================================
Trigger: Timer (runs daily at midnight UTC)

What this does:
  1. Calls LLMaven's extract endpoint to download yesterday's JSONL spend logs
  2. Uploads the raw JSONL to Data Lake under raw/YYYY/MM/DD/
  3. Flattens the nested JSONL into clean rows (one row = one AI interaction)
  4. Saves clean data as Parquet to Data Lake under clean/YYYY/MM/DD/

Environment variables needed (set in Pulumi / Azure portal):
  LLMAVEN_URL       — eScience's LLMaven server URL (e.g. https://llmaven.escience.uw.edu)
  LLMAVEN_API_KEY   — master key to authenticate with LLMaven
  DATA_LAKE_CONN_STR — Azure Data Lake connection string (auto-set by Pulumi)
  RAW_CONTAINER     — "raw"
  CLEAN_CONTAINER   — "clean"
"""

import os
import json
import logging
import io
from datetime import datetime, timedelta, timezone

import azure.functions as func
import pandas as pd
import requests
from azure.storage.blob import BlobServiceClient

# ── Timer trigger: runs every day at midnight UTC ─────────────────────────────
# Cron format: "0 0 0 * * *" = second=0, minute=0, hour=0, every day
app = func.FunctionApp()

@app.timer_trigger(
    schedule="0 0 0 * * *",     # Daily at midnight UTC
    arg_name="timer",
    run_on_startup=False,        # Don't run immediately on deploy
    use_monitor=True,            # Track missed runs if function was down
)
def extract_pipeline(timer: func.TimerRequest) -> None:
    """Main pipeline: extract → upload raw → clean → upload clean"""

    if timer.past_due:
        logging.warning("Timer is past due — running now to catch up.")

    # Always process yesterday (we want complete day's data)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")

    logging.info(f"Starting LLMaven extract pipeline for {date_str}")

    # ── Step 1: Extract raw JSONL from LLMaven ────────────────────────────────
    raw_jsonl = _extract_from_llmaven(date_str)

    if not raw_jsonl:
        logging.warning(f"No data returned for {date_str}. Skipping.")
        return

    # ── Step 2: Upload raw JSONL to Data Lake ─────────────────────────────────
    # Path: raw/2026/03/28/litellm_spend_logs_2026-03-28.jsonl
    raw_blob_path = _make_blob_path("raw", yesterday, f"litellm_spend_logs_{date_str}.jsonl")
    _upload_to_data_lake(
        container=os.environ["RAW_CONTAINER"],
        blob_path=raw_blob_path,
        data=raw_jsonl.encode("utf-8"),
        content_type="application/jsonl",
    )
    logging.info(f"Uploaded raw JSONL to {raw_blob_path}")

    # ── Step 3: Clean and flatten the JSONL ───────────────────────────────────
    records = [json.loads(line) for line in raw_jsonl.strip().splitlines() if line.strip()]
    clean_df = _clean_records(records)
    logging.info(f"Cleaned {len(clean_df)} records for {date_str}")

    # ── Step 4: Upload clean Parquet to Data Lake ─────────────────────────────
    # Why Parquet over CSV?
    #   • 85% smaller file size (columnar compression)
    #   • 10x faster to query (only reads columns you need)
    #   • Preserves types (int/float/datetime — no parsing needed later)
    clean_blob_path = _make_blob_path("clean", yesterday, f"llmaven_clean_{date_str}.parquet")
    parquet_buffer = io.BytesIO()
    clean_df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
    _upload_to_data_lake(
        container=os.environ["CLEAN_CONTAINER"],
        blob_path=clean_blob_path,
        data=parquet_buffer.getvalue(),
        content_type="application/octet-stream",
    )
    logging.info(f"Uploaded clean Parquet to {clean_blob_path}")
    logging.info(f"Pipeline complete for {date_str} — {len(clean_df)} interactions processed.")


def _extract_from_llmaven(date_str: str) -> str | None:
    """
    Download spend logs from LLMaven for a given date.

    If LLMAVEN_URL is not set (local demo mode), returns our test data instead.
    This lets the pipeline run end-to-end even without real credentials.
    """
    llmaven_url = os.environ.get("LLMAVEN_URL", "").strip()

    # ── Demo mode: no real LLMaven URL configured ─────────────────────────────
    if not llmaven_url:
        logging.warning("LLMAVEN_URL not set — using demo test data.")
        return _get_demo_data()

    # ── Real mode: call LLMaven extract endpoint ───────────────────────────────
    api_key = os.environ.get("LLMAVEN_API_KEY", "")
    url = f"{llmaven_url}/api/v1/extract/litellm"

    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            params={"date": date_str},
            timeout=60,
        )
        response.raise_for_status()
        return response.text

    except requests.RequestException as e:
        logging.error(f"Failed to extract from LLMaven: {e}")
        return None


def _clean_records(records: list[dict]) -> pd.DataFrame:
    """
    Flatten nested JSONL records into a clean table.

    Input (one record):
      {
        "session_id": "abc123",
        "model": "anthropic/claude-sonnet-4-6",
        "spend": 0.004794,
        "prompt_tokens": 13,
        "completion_tokens": 317,
        "startTime": "2026-03-28T10:00:00",
        "request_tags": ["User-Agent: Claude-Code"],
        "proxy_server_request": {
          "messages": [{"role": "user", "content": "..."}]
        },
        ...
      }

    Output (one clean row per record):
      | date | session_id | model | cost | prompt_tokens | completion_tokens | total_tokens | turns | source | user |
    """
    clean_rows = []

    for r in records:
        # Count conversation turns (how many messages in this session)
        messages = []
        proxy_req = r.get("proxy_server_request") or {}
        if isinstance(proxy_req, dict):
            messages = proxy_req.get("messages") or []
        turns = len([m for m in messages if m.get("role") == "user"])

        # Extract source app from request_tags (e.g. "Claude-Code", "curl", "python-httpx")
        tags = r.get("request_tags") or []
        source = "unknown"
        for tag in tags:
            if "Claude-Code" in str(tag):
                source = "Claude-Code"
                break
            elif "curl" in str(tag):
                source = "curl"
                break
            elif "python" in str(tag).lower():
                source = "python-script"
                break
            elif "safemind" in str(tag).lower():
                source = "SafeMind"
                break

        # Clean up model name (remove provider prefix)
        model = r.get("model") or "unknown"
        model_clean = model.split("/")[-1] if "/" in model else model

        clean_rows.append({
            "date":               r.get("startTime", "")[:10],   # Just the date part
            "session_id":         r.get("session_id") or "",
            "request_id":         r.get("request_id") or "",
            "user":               r.get("user") or "unknown",
            "model":              model_clean,
            "model_full":         model,
            "cost_usd":           float(r.get("spend") or 0),
            "prompt_tokens":      int(r.get("prompt_tokens") or 0),
            "completion_tokens":  int(r.get("completion_tokens") or 0),
            "total_tokens":       int(r.get("total_tokens") or 0),
            "turns":              turns,
            "source":             source,                          # Claude-Code / SafeMind / curl / etc.
            "cache_hit":          bool(r.get("cache_hit") or False),
            "start_time":         r.get("startTime") or "",
            "end_time":           r.get("endTime") or "",
        })

    df = pd.DataFrame(clean_rows)

    # Convert types
    if not df.empty:
        df["date"]       = pd.to_datetime(df["date"])
        df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
        df["end_time"]   = pd.to_datetime(df["end_time"],   errors="coerce")
        df["duration_s"] = (df["end_time"] - df["start_time"]).dt.total_seconds()

    return df


def _upload_to_data_lake(container: str, blob_path: str, data: bytes, content_type: str) -> None:
    """Upload bytes to Azure Data Lake Storage Gen2."""
    conn_str = os.environ["DATA_LAKE_CONN_STR"]
    client = BlobServiceClient.from_connection_string(conn_str)
    blob_client = client.get_blob_client(container=container, blob=blob_path)
    blob_client.upload_blob(data, overwrite=True, content_settings={"content_type": content_type})


def _make_blob_path(stage: str, date: datetime, filename: str) -> str:
    """
    Build a partitioned path for the Data Lake.
    e.g. raw/2026/03/28/litellm_spend_logs_2026-03-28.jsonl
    Partitioning by year/month/day makes queries faster — only scan what you need.
    """
    return f"{stage}/{date.year:04d}/{date.month:02d}/{date.day:02d}/{filename}"


def _get_demo_data() -> str:
    """
    Returns sample JSONL records for demo/testing when no LLMaven URL is configured.
    Same format as real LLMaven data so the pipeline runs end-to-end.
    """
    demo_records = [
        {
            "request_id": "chatcmpl-demo-001",
            "session_id": "session-abc-001",
            "model": "anthropic/claude-sonnet-4-6",
            "spend": 0.004794,
            "prompt_tokens": 150,
            "completion_tokens": 317,
            "total_tokens": 467,
            "startTime": "2026-03-28T10:00:00",
            "endTime":   "2026-03-28T10:00:02",
            "user": "researcher_01",
            "request_tags": ["User-Agent: Claude-Code", "User-Agent: claude-code/1.0"],
            "cache_hit": False,
            "proxy_server_request": {
                "model": "anthropic/claude-sonnet-4-6",
                "messages": [
                    {"role": "system",    "content": "You are a research software engineering assistant."},
                    {"role": "user",      "content": "How do I write a pytest fixture?"},
                ]
            }
        },
        {
            "request_id": "chatcmpl-demo-002",
            "session_id": "session-abc-001",
            "model": "anthropic/claude-sonnet-4-6",
            "spend": 0.008210,
            "prompt_tokens": 480,
            "completion_tokens": 520,
            "total_tokens": 1000,
            "startTime": "2026-03-28T10:01:00",
            "endTime":   "2026-03-28T10:01:03",
            "user": "researcher_01",
            "request_tags": ["User-Agent: Claude-Code"],
            "cache_hit": False,
            "proxy_server_request": {
                "messages": [
                    {"role": "system",    "content": "You are a research software engineering assistant."},
                    {"role": "user",      "content": "How do I write a pytest fixture?"},
                    {"role": "assistant", "content": "Here is how you write a fixture..."},
                    {"role": "user",      "content": "Can you show me a parametrized example?"},
                ]
            }
        },
        {
            "request_id": "chatcmpl-demo-003",
            "session_id": "session-xyz-002",
            "model": "anthropic/claude-sonnet-4-6",
            "spend": 0.002100,
            "prompt_tokens": 90,
            "completion_tokens": 180,
            "total_tokens": 270,
            "startTime": "2026-03-28T11:00:00",
            "endTime":   "2026-03-28T11:00:01",
            "user": "safemind_bot",
            "request_tags": ["User-Agent: python-httpx", "safemind"],
            "cache_hit": False,
            "proxy_server_request": {
                "messages": [
                    {"role": "user", "content": "Evaluate this response for mental health safety..."},
                ]
            }
        },
    ]
    return "\n".join(json.dumps(r) for r in demo_records)
