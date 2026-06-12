# LLMoxie | LLM Observability Pipeline

Real-time observability for [LLMaven](https://github.com/uw-ssec/llmaven), an open-source LLM gateway built at the UW eScience Institute for the [NAIRR](https://nairrpilot.org/) initiative.

Every API call through the gateway is captured, processed, and surfaced on a live dashboard. Researchers and administrators get full visibility into model usage, cost, and session behavior across 13,000+ research sessions.

**Live dashboard:** https://llmaven-prod-streamlit.azurewebsites.net

---

## Quick Start

The dashboard runs standalone — no Kafka or Redis required for local exploration.

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

To run the full pipeline locally (Kafka + Redis), see [Running the full pipeline](#running-the-full-pipeline) below.

---

## What it does

When a researcher calls an LLM through LLMaven, LiteLLM fires a callback on completion. That callback publishes a structured usage event to Kafka. A consumer picks it up, normalizes it, and fans it out to two stores:

- **Redis** (hot layer): live dashboard reads, session lookups, per-user hourly cost alerts
- **Azure Data Lake** (cold layer): full history in partitioned Parquet, queried via Synapse SQL

KEDA watches the Kafka consumer group lag and automatically scales consumer pods up under load and back down when the queue clears.

```
LLMaven gateway
    |
    | LiteLLM callback (non-blocking)
    v
Kafka  (topic: llm.usage.raw, partitioned by user_id)
    |
    | KEDA scales consumers based on lag
    v
Consumer (normalize, compute derived fields, fan-out)
    |               |
    v               v
Redis (hot)     Azure Data Lake (cold)
    |               |
    v               v
Live dashboard  Synapse SQL (trend queries)
```

---

## Dashboard Features

- Model usage breakdown by AI model
- Daily and hourly cost trends
- Token distribution: input vs. output per session
- Top users by cost
- Session length and turn count distributions
- Source attribution (Claude Code, curl, Python scripts, etc.)
- Real-time cost alerting via Slack or email

---

## Repo Structure

```
kafka/
  producer.py       LiteLLM callback -> Kafka publisher
  consumer.py       Kafka -> Redis + Azure Data Lake
  requirements.txt

k8s/
  kafka.yaml        Kafka on Kubernetes (KRaft mode)
  redis.yaml        Redis 7.2
  consumer.yaml     Consumer deployment
  keda-scaler.yaml  KEDA ScaledObject (scales on consumer group lag)

pulumi/
  __main__.py       Azure infrastructure (Data Lake, Function App, Container Apps)

function_app/
  extract_pipeline/ Azure Function: daily batch extract to Data Lake

dashboard/
  app.py            Streamlit dashboard (Redis + Azure Synapse)
  Dockerfile
  requirements.txt

test-extract-output/
  *.jsonl           Sample data for local development
```

---

## Running the Full Pipeline

### Kafka consumer

```bash
cd kafka
pip install -r requirements.txt

export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export REDIS_HOST=localhost
export DATA_LAKE_CONN_STR=your_connection_string

python -m kafka.consumer
```

### Kubernetes (Kafka + Redis + KEDA)

```bash
kubectl create namespace llmaven
kubectl apply -f k8s/kafka.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/consumer.yaml

# Install KEDA first: https://keda.sh/docs/deploy/
kubectl apply -f k8s/keda-scaler.yaml
```

### Azure infrastructure (Pulumi)

```bash
cd pulumi
pip install -r requirements.txt
pulumi stack init dev
pulumi config set azure-native:location westus2
pulumi config set llmaven_url "https://your-llmaven-server"
pulumi config set --secret llmaven_api_key "sk-your-key"
pulumi up
```

---

## Design Decisions

**Push over poll.** LiteLLM's callback fires on every call completion. Publishing to Kafka from the callback means the gateway never blocks on the observability layer, even under traffic spikes.

**Offset commit after fan-out.** The consumer commits the Kafka offset only after both the Redis write and the Data Lake write succeed. If the process crashes mid-write, Kafka replays the event on restart so neither store misses data.

**Two-tier storage.** Redis holds exactly the data the live dashboard and alerting need (sorted sets for cost rankings, hashes for session state, hourly accumulators). Azure Data Lake holds the full history for trend analysis via Synapse SQL, where Redis would be wasteful.

**KEDA autoscaling.** Consumer instances don't self-scale. KEDA watches consumer group lag and adds pods when it crosses the threshold, then removes them when the queue drains. No manual capacity planning.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Event streaming | Apache Kafka (self-hosted, KRaft mode) |
| Autoscaling | KEDA (Kubernetes Event Driven Autoscaler) |
| Hot storage | Redis (sorted sets, hashes, expiring keys) |
| Cold storage | Azure Data Lake Storage Gen2 (partitioned Parquet) |
| Analytics | Azure Synapse Analytics |
| Infrastructure | Pulumi (Python) |
| Dashboard | Streamlit on Azure Container Apps |
| Batch pipeline | Azure Functions (daily timer trigger) |
