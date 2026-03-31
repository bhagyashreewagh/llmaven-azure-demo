# Azure Pipeline Architecture — LLMaven Data Pipeline
## Resource Comparison & Decision Guide

---

## The Data Flow

```
LLMaven (LiteLLM PostgreSQL)
            ↓
    STAGE 1: INGESTION
    (how do we pull the data?)
            ↓
    STAGE 2: RAW STORAGE
    (where do we dump the raw JSONL files?)
            ↓
    STAGE 3: PROCESSING
    (how do we clean messy nested JSONL → clean rows?)
            ↓
    STAGE 4: ANALYTICAL STORAGE
    (where do we store clean data for querying?)
            ↓
    STAGE 5: DASHBOARD
    (how do we visualize it?)
```

---

## STAGE 1 — Ingestion (Pulling Data from LLMaven)

> **Goal:** Automatically run `llmaven infra extract` on a schedule and move the data to Azure

| Resource | What It Does | Key Limits | Storage | Cost |
|---|---|---|---|---|
| **Azure Data Factory (ADF)** | Enterprise-grade pipeline orchestrator. Schedules jobs, moves data between sources, handles failures, retries, logging. Can run custom scripts (like our llmaven CLI). | Up to 10,000 pipeline runs/month on free tier | No built-in storage — just orchestrates movement | ~$1/1000 pipeline runs + compute |
| **Azure Logic Apps** | Visual drag-and-drop workflow builder. Good for simple triggers (e.g. "every Monday run this"). Less flexible than ADF for custom code. | 4,000 actions/month free | No storage | ~$0.000025/action |
| **Azure Functions** | Serverless — runs a piece of code on a schedule (like a cron job). You write Python/Node code that calls the llmaven CLI and uploads results. | 1 million executions/month free | No storage | Practically free at this scale |
| **Azure Databricks** | Big data processing platform. Massive overkill for our use case — built for TB-scale data. | No meaningful limit | No | Expensive (~$0.40/hour minimum) |

### ✅ We Choose: **Azure Functions**

**Why:**
- Our pipeline is simple — run a Python script, upload a file. That's it.
- Azure Functions is literally built for this: "run this code on a schedule."
- 1 million free executions/month — we'd use maybe 30 (once a day).
- No servers to manage, no complex setup.
- ADF is powerful but overkill — it's designed for enterprises moving massive datasets between 50 systems.

**What it does in our pipeline:**
```
Every day at midnight →
  Azure Function wakes up →
  Runs llmaven extract for yesterday →
  Gets JSONL file →
  Uploads to Azure Data Lake →
  Goes back to sleep
```

---

## STAGE 2 — Raw Storage (Where the JSONL Files Live)

> **Goal:** Store raw JSONL files as-is, cheap, durable, accessible

| Resource | What It Does | Storage Capacity | Storage Duration | Storage Types | Cost |
|---|---|---|---|---|---|
| **Azure Data Lake Storage Gen2 (ADLS Gen2)** | Hierarchical file system built on top of Blob Storage. Designed for big data analytics. Organizes files in folders like a real filesystem. Works natively with all Azure analytics tools. | Unlimited (petabyte scale) | Forever (until deleted) | Hot, Cool, Archive tiers | ~$0.018/GB/month (Hot) |
| **Azure Blob Storage** | Flat object storage — like S3 on AWS. No folder hierarchy (just flat containers). Simpler but less organized for analytics. ADLS Gen2 is actually built on top of this. | Unlimited | Forever | Hot, Cool, Archive tiers | ~$0.018/GB/month (Hot) |
| **Azure Files** | Cloud file share — acts like a network drive you can mount. Great for sharing files between VMs. Not ideal for analytics pipelines. | 100TB per share | Forever | Standard, Premium | ~$0.06/GB/month |
| **Azure SQL Database** | Relational database. Could store JSONL as raw text but that's wasteful and defeats the purpose of a database. | 32GB–4TB | Forever | General Purpose, Serverless | ~$15/month minimum |
| **Azure Table Storage** | NoSQL key-value store. Very cheap but limited querying. Not great for nested JSON analytics. | 500TB | Forever | Standard only | ~$0.045/10GB/month |

### Storage Tier Explanation (applies to Blob/ADLS)

| Tier | Access Speed | Cost | Best For |
|---|---|---|---|
| **Hot** | Instant | Higher storage, low access cost | Data you read frequently |
| **Cool** | Instant | Lower storage, higher access cost | Data accessed once a month |
| **Archive** | Hours (rehydration needed) | Very cheap storage | Old data you rarely touch |

### ✅ We Choose: **Azure Data Lake Storage Gen2 (ADLS Gen2)**

**Why:**
- Designed exactly for this use case — storing raw analytics files (JSONL, CSV, Parquet)
- Hierarchical folders means we can organize nicely:
  ```
  llmaven-raw/
  ├── 2026/
  │   ├── 01/
  │   │   ├── litellm_spend_logs_2026-01-01.jsonl
  │   │   └── litellm_spend_logs_2026-01-02.jsonl
  │   └── 02/
  │       └── ...
  ```
- Works natively with Azure Data Factory, Synapse, Databricks — no connectors needed
- Same price as Blob Storage but far more powerful for analytics
- Start with **Hot** tier — our dataset is tiny (a few MB/day)

**Cost estimate for our use case:**
- ~1MB of JSONL per day → ~365MB/year → **less than $0.01/month**

---

## STAGE 3 — Processing (Cleaning Messy JSONL → Clean Rows)

> **Goal:** Take nested messy JSONL and flatten it into clean tables (one row = one AI interaction)

**The problem:** Raw JSONL looks like this:
```json
{
  "session_id": "abc123",
  "proxy_server_request": {
    "messages": [{"role": "user", "content": "..."}]
  },
  "metadata": {"user_api_key_alias": "...", "headers": {...}}
}
```
We need clean rows like:
```
| date | user | model | tokens | cost | turns | session_id |
```

| Resource | What It Does | Scale | Cost |
|---|---|---|---|
| **Azure Functions** | Run a Python script that reads JSONL, flattens it with pandas, writes clean CSV/Parquet back to Data Lake | Up to 1M executions free | Practically free |
| **Azure Data Factory Data Flows** | Visual drag-and-drop data transformation tool inside ADF. No code needed but limited flexibility for deeply nested JSON. | Unlimited | ~$0.228/hour of compute |
| **Azure Databricks** | Apache Spark-based big data processing. Handles TB-scale transformations. Massive overkill for our data size. | Unlimited | ~$0.40+/hour |
| **Azure Synapse Analytics** | Combined data warehouse + Spark processing. Enterprise scale. Way too big for us. | Unlimited | ~$5+/hour |
| **Azure HDInsight** | Managed Hadoop/Spark clusters. Old, being deprecated. Avoid. | Unlimited | Expensive |

### ✅ We Choose: **Azure Functions (again)**

**Why:**
- We're flattening a few thousand JSON records — this is a 5-second Python script, not a big data problem
- The same Azure Function that does ingestion can do the cleaning in the same run:
  ```
  Extract JSONL → clean it with pandas → save clean Parquet to Data Lake
  ```
- Free, fast, simple
- If data ever grows to millions of records, we can swap to Databricks later — but not now

**The cleaning script does:**
```python
import pandas as pd, json

records = [json.loads(line) for line in open('raw.jsonl')]

clean = [{
    'date':           r['startTime'],
    'session_id':     r['session_id'],
    'user':           r['user'],
    'model':          r['model'],
    'prompt_tokens':  r['prompt_tokens'],
    'completion_tokens': r['completion_tokens'],
    'cost':           r['spend'],
    'turns':          len(r['proxy_server_request']['messages']),
    'source':         str(r['request_tags'])
} for r in records]

pd.DataFrame(clean).to_parquet('clean.parquet')
```

---

## STAGE 4 — Analytical Storage (Clean Data for Querying)

> **Goal:** Store clean data somewhere fast and queryable so the dashboard can read it

| Resource | What It Does | Storage | Query Language | Cost |
|---|---|---|---|---|
| **Azure Synapse Analytics (Serverless SQL)** | Query Parquet files directly from Data Lake using SQL — no database needed. Pay per query, not per hour. | Reads from Data Lake | SQL | $5 per TB scanned (our data = fractions of a cent) |
| **Azure SQL Database** | Traditional relational database. Load clean CSV/Parquet into tables. Always-on server. | 32GB–4TB | SQL | ~$15/month minimum (even when idle) |
| **Azure Cosmos DB** | NoSQL document database. Good for JSON but expensive and complex for analytics. | Unlimited | SQL-like | ~$25/month minimum |
| **Azure Data Explorer (Kusto)** | Time-series and log analytics database. Very fast for time-based queries. But complex to set up. | Unlimited | KQL (different language) | ~$0.005/hour minimum |
| **Azure Managed PostgreSQL** | Fully managed PostgreSQL. Familiar, powerful. But overkill — we already have clean Parquet files. | 32GB–16TB | SQL | ~$25/month minimum |
| **Parquet files in Data Lake (no DB)** | Just keep the clean Parquet files in Data Lake. Synapse Serverless SQL can query them directly. No separate DB needed. | Unlimited | SQL via Synapse | Near zero |

### ✅ We Choose: **Parquet files in Data Lake + Synapse Serverless SQL**

**Why:**
- We don't need a separate database at all — Synapse can query Parquet files directly with SQL
- No always-on server = no minimum monthly cost
- Pay only when someone runs a query — our tiny dataset costs fractions of a penny per query
- Parquet is a columnar format — much faster and smaller than CSV for analytics:
  ```
  CSV 100MB → Parquet ~15MB (85% smaller, 10x faster to query)
  ```
- Azure SQL Database at $15/month is wasteful when Synapse Serverless is essentially free at our scale

**Final storage structure in Data Lake:**
```
llmaven/
├── raw/                          ← Stage 2: raw JSONL
│   └── 2026/01/01/logs.jsonl
└── clean/                        ← Stage 4: clean Parquet
    └── 2026/01/01/clean.parquet
```

---

## STAGE 5 — Dashboard (Visualization)

> **Goal:** Show charts like Carlos made — cost over time, model usage, tokens, session turns

| Resource | What It Does | Data Sources | Cost |
|---|---|---|---|
| **Power BI** | Microsoft's enterprise dashboard tool. Connects natively to all Azure services. Drag-and-drop charts. Shareable links. | Azure Synapse, Data Lake, SQL | Free (Desktop) / ~$10/user/month (Pro for sharing) |
| **Azure Managed Grafana** | Open-source Grafana hosted by Azure. Better for time-series/metrics dashboards. More technical to set up. | Synapse, SQL, Prometheus | ~$9/month |
| **Azure Static Web App + Python** | Build a custom dashboard using Python (Plotly/Dash) or React. Full control but more work. | Anything | Free hosting |
| **Streamlit on Azure Container Apps** | Python-based dashboard framework. Very fast to build. Host as a container on Azure. | Parquet, SQL, anything | ~$5/month |
| **Jupyter Notebooks (Azure ML)** | Not really a dashboard — more for exploration like Carlos did. Not shareable as a live dashboard. | Anything | Free tier available |

### ✅ We Choose: **Streamlit on Azure Container Apps**

**Why:**
- We can replicate Carlos's charts in Python (which we already know from the cleaning step)
- Streamlit turns a Python script into a web dashboard in ~20 lines of code
- No drag-and-drop limitations — full flexibility for custom charts
- Azure Container Apps is serverless — scales to zero when nobody is looking at it (free when idle)
- Power BI is great but requires Pro license (~$10/user/month) to share with the team
- Grafana is better suited for real-time metrics, not batch analytics

**What the dashboard shows:**
```
┌─────────────────────────────────────────┐
│  LLMaven Usage Dashboard                │
├─────────────┬───────────────────────────┤
│ Model Usage │ Claude 94% / Others 6%    │
│ Cost/Day    │ Line chart over time      │
│ Tokens      │ Input vs Output bar chart │
│ Sessions    │ Turns distribution        │
│ Top Users   │ By spend / by calls       │
└─────────────┴───────────────────────────┘
```

---

## Full Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│ LLMaven Server (LiteLLM + PostgreSQL)                   │
└────────────────────────┬────────────────────────────────┘
                         │ llmaven infra extract (daily)
                         ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 1: Azure Functions (Ingestion + Processing)       │
│ • Runs daily at midnight (cron trigger)                 │
│ • Calls llmaven extract → gets JSONL                    │
│ • Cleans JSONL → Parquet with pandas                    │
│ • Uploads both raw + clean to Data Lake                 │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 2+4: Azure Data Lake Storage Gen2                 │
│ llmaven/                                                │
│ ├── raw/2026/01/01/logs.jsonl    ← raw files            │
│ └── clean/2026/01/01/clean.parquet ← clean files       │
└────────────────────────┬────────────────────────────────┘
                         │ SQL queries via Synapse Serverless
                         ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 5: Streamlit Dashboard (Azure Container Apps)     │
│ • Reads Parquet from Data Lake                          │
│ • Shows: model usage, cost, tokens, sessions            │
│ • Shareable URL for the whole team                      │
└─────────────────────────────────────────────────────────┘
```

---

## Total Cost Estimate (Monthly)

| Component | Resource | Estimated Cost |
|---|---|---|
| Ingestion + Processing | Azure Functions | **Free** (well within free tier) |
| Raw + Clean Storage | ADLS Gen2 Hot tier | **~$0.01/month** |
| Querying | Synapse Serverless SQL | **~$0.01/month** |
| Dashboard | Container Apps (scales to zero) | **~$2–5/month** |
| **TOTAL** | | **~$2–5/month** |

Compare to naive approach:
- Azure SQL Database always-on: ~$15/month
- Power BI Pro for sharing: ~$10/user/month
- Azure Databricks: ~$100+/month

**We save ~$120+/month by choosing the right tools for the scale of this project.**

---

## What We Would Change If Data Grew 100x

| Stage | Current Choice | If Data Grew |
|---|---|---|
| Ingestion | Azure Functions | Azure Data Factory |
| Processing | Azure Functions + pandas | Azure Databricks |
| Storage | ADLS Gen2 Hot | ADLS Gen2 Cool (cheaper for large volumes) |
| Querying | Synapse Serverless | Synapse Dedicated Pool |
| Dashboard | Streamlit | Power BI (better for large orgs) |
