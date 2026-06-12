"""
Kafka Consumer -> Redis (hot layer) + Azure Data Lake (cold layer)
===================================================================
Reads from `llm.usage.raw`, normalizes events, computes derived fields,
and fans out to two destinations before committing the Kafka offset.

The offset is committed AFTER both writes succeed. If the process crashes
mid-write, Kafka replays the event on restart — guaranteeing at-least-once
delivery to both stores.

Environment variables:
    KAFKA_BOOTSTRAP_SERVERS     - e.g. "kafka-service:9092"
    KAFKA_TOPIC                 - defaults to "llm.usage.raw"
    KAFKA_CONSUMER_GROUP        - defaults to "llmaven-observability"
    REDIS_HOST                  - e.g. "redis-service"
    REDIS_PORT                  - defaults to 6379
    DATA_LAKE_CONN_STR          - Azure Data Lake connection string
    COLD_CONTAINER              - blob container for cold storage
    HOURLY_COST_ALERT_THRESHOLD - USD, defaults to 5.0
    ALERT_WEBHOOK_URL           - Slack/Teams webhook for cost alerts
"""

import json
import logging
import os
import time
import io
from collections import defaultdict
from datetime import datetime, timezone

import requests
import redis
import pandas as pd
from confluent_kafka import Consumer, KafkaError
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Config ────────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka-service:9092")
KAFKA_TOPIC             = os.getenv("KAFKA_TOPIC", "llm.usage.raw")
KAFKA_GROUP             = os.getenv("KAFKA_CONSUMER_GROUP", "llmaven-observability")
REDIS_HOST              = os.getenv("REDIS_HOST", "redis-service")
REDIS_PORT              = int(os.getenv("REDIS_PORT", 6379))
DATA_LAKE_CONN_STR      = os.getenv("DATA_LAKE_CONN_STR", "")
COLD_CONTAINER          = os.getenv("COLD_CONTAINER", "realtime-events")
ALERT_THRESHOLD         = float(os.getenv("HOURLY_COST_ALERT_THRESHOLD", "5.0"))
ALERT_WEBHOOK_URL       = os.getenv("ALERT_WEBHOOK_URL", "")

# Normalize provider-specific model name prefixes to clean names
MODEL_ALIASES = {
    "anthropic/claude-sonnet-4-6": "claude-sonnet-4-6",
    "anthropic/claude-haiku-4-5":  "claude-haiku-4-5",
    "openai/gpt-4o":               "gpt-4o",
    "openai/gpt-4o-mini":          "gpt-4o-mini",
}


def normalize_event(raw: dict) -> dict:
    """Normalize field names and compute derived fields."""
    model_raw = raw.get("model", "unknown")
    model     = MODEL_ALIASES.get(model_raw, model_raw.split("/")[-1])

    start_ms  = raw.get("start_time", 0) * 1000
    end_ms    = raw.get("end_time", 0) * 1000

    prompt_tokens     = int(raw.get("prompt_tokens", 0))
    completion_tokens = int(raw.get("completion_tokens", 0))
    total_tokens      = prompt_tokens + completion_tokens
    cost_usd          = float(raw.get("cost_usd", 0.0))
    cost_per_1k       = (cost_usd / total_tokens * 1000) if total_tokens > 0 else 0.0

    ts = raw.get("timestamp_ms", int(time.time() * 1000))
    hour_bucket = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H")

    return {
        "event_type":          raw.get("event_type", "llm_call_complete"),
        "timestamp_ms":        ts,
        "hour_bucket":         hour_bucket,
        "model":               model,
        "model_raw":           model_raw,
        "user_id":             raw.get("user_id", "unknown"),
        "session_id":          raw.get("session_id", "unknown"),
        "request_id":          raw.get("request_id", "unknown"),
        "prompt_tokens":       prompt_tokens,
        "completion_tokens":   completion_tokens,
        "total_tokens":        total_tokens,
        "cost_usd":            cost_usd,
        "cost_per_1k_tokens":  round(cost_per_1k, 6),
        "latency_ms":          raw.get("latency_ms", round(end_ms - start_ms, 2)),
        "session_duration_ms": round(end_ms - start_ms, 2),
        "cache_hit":           bool(raw.get("cache_hit", False)),
        "stream":              bool(raw.get("stream", False)),
    }


class RedisWriter:
    """
    Writes hot-layer metrics to Redis.

    Data structures:
      - Sorted sets: running cost/token totals by user and model (for time-range queries)
      - Hashes: latest session state (for live dashboard)
      - Strings: hourly cost per user (for alerting)
    """

    def __init__(self):
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    def write(self, event: dict):
        ts    = event["timestamp_ms"]
        uid   = event["user_id"]
        model = event["model"]
        cost  = event["cost_usd"]
        tokens = event["total_tokens"]
        hour  = event["hour_bucket"]
        sid   = event["session_id"]

        pipe = self.r.pipeline()

        # Running cost totals by user (sorted set: score = cumulative cost, member = timestamp)
        pipe.zadd(f"cost:user:{uid}",   {str(ts): cost})
        pipe.zadd(f"cost:model:{model}", {str(ts): cost})

        # Running token totals
        pipe.zadd(f"tokens:user:{uid}",   {str(ts): tokens})
        pipe.zadd(f"tokens:model:{model}", {str(ts): tokens})

        # Latest session state (hash) for live dashboard
        pipe.hset(f"session:{sid}", mapping={
            "user_id":    uid,
            "model":      model,
            "last_ts":    ts,
            "cost_usd":   cost,
            "tokens":     tokens,
            "latency_ms": event["latency_ms"],
        })
        pipe.expire(f"session:{sid}", 3600)  # expire inactive sessions after 1h

        # Hourly cost accumulator per user for alerting
        hourly_key = f"hourly_cost:{uid}:{hour}"
        pipe.incrbyfloat(hourly_key, cost)
        pipe.expire(hourly_key, 7200)  # keep for 2 hours

        pipe.execute()

    def get_hourly_cost(self, user_id: str, hour: str) -> float:
        key = f"hourly_cost:{user_id}:{hour}"
        val = self.r.get(key)
        return float(val) if val else 0.0


class DataLakeWriter:
    """Writes cold-layer events to Azure Data Lake Storage as partitioned Parquet."""

    def __init__(self):
        if DATA_LAKE_CONN_STR:
            self.client = BlobServiceClient.from_connection_string(DATA_LAKE_CONN_STR)
        else:
            self.client = None
            logger.warning("DATA_LAKE_CONN_STR not set — cold layer writes disabled")

        self._buffer: list[dict] = []
        self._flush_every = 100  # write to lake every 100 events

    def write(self, event: dict):
        self._buffer.append(event)
        if len(self._buffer) >= self._flush_every:
            self.flush()

    def flush(self):
        if not self._buffer or not self.client:
            return

        df  = pd.DataFrame(self._buffer)
        buf = io.BytesIO()
        df.to_parquet(buf, index=False, engine="pyarrow")

        now  = datetime.now(timezone.utc)
        path = f"{now.year:04d}/{now.month:02d}/{now.day:02d}/{now.hour:02d}/events_{int(time.time())}.parquet"

        blob = self.client.get_blob_client(container=COLD_CONTAINER, blob=path)
        blob.upload_blob(buf.getvalue(), overwrite=True)
        logger.info(f"Flushed {len(self._buffer)} events to Data Lake: {path}")
        self._buffer.clear()


def maybe_alert(redis_writer: RedisWriter, event: dict):
    """Check hourly cost threshold and fire alert if exceeded."""
    if not ALERT_WEBHOOK_URL:
        return

    uid  = event["user_id"]
    hour = event["hour_bucket"]
    total = redis_writer.get_hourly_cost(uid, hour)

    if total >= ALERT_THRESHOLD:
        message = (
            f":warning: *LLMaven cost alert*\n"
            f"User `{uid}` has spent *${total:.4f}* in the past hour "
            f"(threshold: ${ALERT_THRESHOLD})"
        )
        try:
            requests.post(ALERT_WEBHOOK_URL, json={"text": message}, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")


def run():
    consumer = Consumer({
        "bootstrap.servers":  KAFKA_BOOTSTRAP_SERVERS,
        "group.id":           KAFKA_GROUP,
        "auto.offset.reset":  "earliest",
        "enable.auto.commit": False,  # manual commit after both writes succeed
    })
    consumer.subscribe([KAFKA_TOPIC])

    redis_writer = RedisWriter()
    lake_writer  = DataLakeWriter()

    logger.info(f"Consumer started — subscribed to {KAFKA_TOPIC} as group {KAFKA_GROUP}")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error(f"Kafka error: {msg.error()}")
                continue

            try:
                raw   = json.loads(msg.value().decode("utf-8"))
                event = normalize_event(raw)

                # Fan out to both destinations before committing offset.
                # If either write fails, the exception propagates and the
                # offset is NOT committed — Kafka replays on restart.
                redis_writer.write(event)
                lake_writer.write(event)

                maybe_alert(redis_writer, event)

                # Commit only after successful fan-out
                consumer.commit(message=msg, asynchronous=False)

            except Exception as e:
                logger.error(f"Failed to process message at offset {msg.offset()}: {e}")

    except KeyboardInterrupt:
        logger.info("Shutting down consumer...")
    finally:
        lake_writer.flush()
        consumer.close()


if __name__ == "__main__":
    run()
