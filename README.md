# LLMoxie — LLM Observability Pipeline

Real-time observability for [LLMaven](https://github.com/uw-ssec/llmaven), an open-source LLM gateway built at the UW eScience Institute for the [NAIRR](https://nairrpilot.org/) initiative. Every usage event is captured the moment it happens, processed in real time, and surfaced on a live dashboard — giving researchers and administrators full visibility into model usage, cost, and session behavior across 13,000+ research sessions.

**Live dashboard:** https://llmaven-prod-streamlit.azurewebsites.net

---

## Architecture

```
LiteLLM Gateway (LLMaven)
        |
        | callback on every API call completion
        v
+------------------------------------------+
|  Kafka Producer  (kafka/producer.py)     |
|  - publishes structured usage events     |
|  - partitioned by user_id               |
|  - topic: llm.usage.raw                 |
+------------------+-----------------------+
                   |
                   v
+------------------------------------------+
|  Kafka (self-hosted on Kubernetes)       |
|  - durable, decoupled from gateway      |
|  - KEDA autoscales consumers on lag     |
+------------------+-----------------------+
                   |
                   v
+------------------------------------------+
|  Kafka Consumer  (kafka/consumer.py)     |
|  - normalizes events across providers   |
|  - computes derived fields              |
|  - fan-out to hot + cold layer          |
|  - commits offset AFTER both writes     |
+--------+--------------------------+------+
         |                          |
         v                          v
+------------------+    +---------------------------+
|  Redis (hot)     |    |  Azure Data Lake (cold)   |
|  sorted sets:    |    |  partitioned Parquet      |
|  cost + tokens   |    |  by date/model            |
|  session hashes  |    |  queried via Synapse SQL  |
|  hourly alerts   |    +---------------------------+
+--------+---------+
         |
         v
+------------------------------------------+
|  Streamlit Dashboard                     |
|  Redis: live metrics (few-second poll)  |
|  Synapse: historical trend queries      |
+------------------------------------------+
```

**KEDA** (Kubernetes Event Driven Autoscaler) watches consumer group lag on `llm.usage.raw` and automatically scales the consumer deployment up when events pile up, and back down when the queue clears.

---

## Repo Structure

```
kafka/
  producer.py         LiteLLM callback -> Kafka publisher
  consumer.py         Kafka -> Redis (hot) + Azure Data Lake (cold)
  requirements.txt

k8s/
  kafka.yaml          Kafka deployment on Kubernetes
  redis.yaml          Redis deployment
  consumer.yaml       Consumer deployment manifest
  keda-scaler.yaml    KEDA ScaledObject (scales on consumer group lag)

pulumi/
  __main__.py         Azure infrastructure as code (Data Lake, Function App, Container Apps)
  Pulumi.yaml
  Pulumi.dev.yaml

function_app/
  extract_pipeline/
    __init__.py       Azure Function: daily batch extract -> Data Lake (batch pipeline)

dashboard/
  app.py              Streamlit dashboard (Redis + Azure Synapse)
  Dockerfile
  requirements.txt

test-extract-output/
  litellm_spend_logs_*.jsonl   Sample data for local dev
```

---

## Key Design Decisions

**Push over poll:** LiteLLM's callback fires on every call completion. Publishing to Kafka from the callback means the gateway never blocks waiting on the observability layer, even under traffic spikes.

**Offset commit after fan-out:** The consumer commits the Kafka offset only after both the Redis write and the Data Lake write succeed. If the process crashes mid-write, Kafka replays the event on restart — neither store misses an event.

**Two-tier storage:** Redis is optimized for the exact queries the live dashboard and alerting service need (sorted sets for cost-by-user, hashes for session state, per-user hourly accumulators). Azure Data Lake holds the full history for trend analysis via Synapse SQL.

**KEDA autoscaling:** Consumer instances don't scale themselves. KEDA watches consumer group lag and spins up more consumer pods when lag exceeds the threshold, absorbing usage spikes without backpressure.

---

## Running Locally

### Streamlit dashboard (no Kafka or Redis needed)

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

### Kafka consumer (requires Kafka + Redis)

```bash
cd kafka
pip install -r requirements.txt

export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export REDIS_HOST=localhost
export DATA_LAKE_CONN_STR=your_connection_string

python -m kafka.consumer
```

### Deploy Kubernetes resources

```bash
kubectl create namespace llmaven
kubectl apply -f k8s/kafka.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/consumer.yaml

# Install KEDA first: https://keda.sh/docs/deploy/
kubectl apply -f k8s/keda-scaler.yaml
```

### Deploy Azure infrastructure

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

## Dashboard Features

- Model usage breakdown (which AI models are called most)
- Daily and hourly cost trends
- Token distribution: input vs. output per session
- Top users by cost
- Session length and turn count distributions
- Source attribution (Claude Code, curl, Python scripts, etc.)
- Real-time cost alerting via Slack/email webhook

---

## Tech Stack

| Layer | Technology |
|---|---|
| Streaming | Apache Kafka (self-hosted on Kubernetes) |
| Autoscaling | KEDA (Kubernetes Event Driven Autoscaler) |
| Hot storage | Redis (sorted sets, hashes, expiring keys) |
| Cold storage | Azure Data Lake Storage Gen2 (partitioned Parquet) |
| Analytics | Azure Synapse Analytics |
| Infrastructure | Pulumi (Python) |
| Dashboard | Streamlit on Azure Container Apps |
| Batch pipeline | Azure Functions (Timer trigger, daily) |
