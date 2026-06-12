"""
LiteLLM Callback -> Kafka Producer
====================================
Registers a custom callback with LiteLLM so every API call completion
publishes a structured event to the Kafka topic `llm.usage.raw`.

Usage (in your LiteLLM proxy config or startup):
    from kafka.producer import LLMUsageCallback
    import litellm
    litellm.callbacks = [LLMUsageCallback()]

Environment variables:
    KAFKA_BOOTSTRAP_SERVERS  - e.g. "kafka-service:9092"
    KAFKA_TOPIC              - defaults to "llm.usage.raw"
"""

import json
import os
import logging
import time
from typing import Any

from confluent_kafka import Producer
from litellm.integrations.custom_logger import CustomLogger

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka-service:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "llm.usage.raw")


def _delivery_report(err, msg):
    if err:
        logger.error(f"Kafka delivery failed for offset {msg.offset()}: {err}")


class LLMUsageCallback(CustomLogger):
    """
    LiteLLM custom callback that fires on every successful API call.
    Publishes a structured usage event to Kafka asynchronously so the
    gateway is never blocked waiting for the observability layer.
    """

    def __init__(self):
        self.producer = Producer({
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "client.id": "llmaven-gateway",
            "acks": "all",
            "retries": 3,
            "retry.backoff.ms": 200,
        })
        logger.info(f"Kafka producer connected to {KAFKA_BOOTSTRAP_SERVERS}")

    def log_success_event(self, kwargs: dict, response_obj: Any, start_time: float, end_time: float):
        """Called by LiteLLM after every successful completion."""
        try:
            usage = getattr(response_obj, "usage", None) or {}
            event = {
                "event_type":          "llm_call_complete",
                "timestamp_ms":        int(time.time() * 1000),
                "start_time":          start_time,
                "end_time":            end_time,
                "latency_ms":          round((end_time - start_time) * 1000, 2),
                "model":               kwargs.get("model", "unknown"),
                "user_id":             kwargs.get("user", "unknown"),
                "session_id":          kwargs.get("metadata", {}).get("session_id", "unknown"),
                "request_id":          getattr(response_obj, "id", "unknown"),
                "prompt_tokens":       getattr(usage, "prompt_tokens", 0),
                "completion_tokens":   getattr(usage, "completion_tokens", 0),
                "total_tokens":        getattr(usage, "total_tokens", 0),
                "cost_usd":            kwargs.get("response_cost", 0.0),
                "stream":              kwargs.get("stream", False),
                "cache_hit":           kwargs.get("cache_hit", False),
                "tags":                kwargs.get("metadata", {}).get("tags", []),
            }

            # Partition by user_id so same-user events stay ordered on one partition
            partition_key = event["user_id"].encode("utf-8")

            self.producer.produce(
                topic=KAFKA_TOPIC,
                key=partition_key,
                value=json.dumps(event).encode("utf-8"),
                callback=_delivery_report,
            )
            # Non-blocking poll to serve delivery callbacks without waiting
            self.producer.poll(0)

        except Exception as e:
            logger.error(f"Failed to publish usage event to Kafka: {e}")

    def log_failure_event(self, kwargs: dict, response_obj: Any, start_time: float, end_time: float):
        """Optionally track failed calls for error-rate monitoring."""
        try:
            event = {
                "event_type":  "llm_call_failed",
                "timestamp_ms": int(time.time() * 1000),
                "model":        kwargs.get("model", "unknown"),
                "user_id":      kwargs.get("user", "unknown"),
                "error":        str(response_obj),
            }
            self.producer.produce(
                topic=KAFKA_TOPIC,
                key=event["user_id"].encode("utf-8"),
                value=json.dumps(event).encode("utf-8"),
                callback=_delivery_report,
            )
            self.producer.poll(0)
        except Exception as e:
            logger.error(f"Failed to publish failure event to Kafka: {e}")

    def flush(self):
        """Flush remaining messages — call on graceful shutdown."""
        self.producer.flush(timeout=10)
