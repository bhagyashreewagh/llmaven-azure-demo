# Azure Pipeline Architecture: LLMaven Data Pipeline
## Resource Comparison and Decision Guide

---

## The Data Flow

```
LLMaven (LiteLLM + PostgreSQL)
            |
    STAGE 1: INGESTION
    (how do we pull the data?)
            |
    STAGE 2: RAW STORAGE
    (where do we dump the raw JSONL files?)
            |
    STAGE 3: PROCESSING
    (how do we clean messy nested JSONL into clean rows?)
            |
    STAGE 4: ANALYTICAL STORAGE
    (where do we store clean data for querying?)
            |
    STAGE 5: DASHBOARD
    (how do we visualize it?)
```

---

## STAGE 1: Ingestion (Pulling Data from LLMaven)

> **Goal:** Automatically run `llmaven infra extract` on a schedule and move the data to Azure

| Resource | What It Does | Key Limits | Cost |
|---|---|---|---|
| **Azure Data Factory (ADF)** | Enterprise-grade pipeline orchestrator. Schedules jobs, moves data between sources, handles failures, retries, and logging. Can run custom scripts like the llmaven CLI. | Up to 10,000 pipeline runs/month on free tier | ~$1 per 1,000 pipeline runs + compute cost per hour |
| **Azure Logic Apps** | Visual drag-and-drop workflow builder. Good for simple triggers (e.g. run every Monday). Less flexible than ADF for custom code. | 4,000 actions/month free | ~$0.000025 per action |
| **Azure Functions** | Serverless: runs a piece of Python code on a schedule like a cron job. Calls the llmaven CLI and uploads results to storage. | 1 million executions/month free | Free up to 1M executions, then $0.20 per million executions |
| **Azure Databricks** | Big data processing platform. Massive overkill for our use case. Built for TB-scale data. | No meaningful limit | ~$0.40/hour per node minimum |

### We Choose: Azure Functions

**Why:**
- Our pipeline is simple: run a Python script, upload a file. That is it.
- Azure Functions is built for exactly this: run this code on a schedule.
- 1 million free executions/month. We use maybe 30 (once a day).
- No servers to manage, no complex setup.
- ADF is powerful but overkill. It is designed for enterprises moving massive datasets between 50 systems.

**What it does in our pipeline:**
```
Every day at midnight ->
  Azure Function wakes up ->
  Runs llmaven extract for yesterday ->
  Gets JSONL file ->
  Uploads to Azure Data Lake ->
  Goes back to sleep
```

**Cost for our use case:**
- 30 executions/month (daily extract) = well within free tier
- Cost: $0.00/month

---

## STAGE 2: Raw Storage (Where the JSONL Files Live)

> **Goal:** Store raw JSONL files as-is, cheap, durable, accessible

| Resource | What It Does | Storage Capacity | Storage Duration | Cost per GB/month | Cost per access |
|---|---|---|---|---|---|
| **Azure Data Lake Storage Gen2 (ADLS Gen2)** | Hierarchical file system built on top of Blob Storage. Designed for big data analytics. Organizes files in folders like a real filesystem. Works natively with all Azure analytics tools. | Unlimited (petabyte scale) | Forever until deleted | Hot: $0.023/GB, Cool: $0.01/GB, Archive: $0.002/GB | Hot: $0.004 per 10K read ops |
| **Azure Blob Storage** | Flat object storage like S3 on AWS. No folder hierarchy. Simpler but less organized for analytics. ADLS Gen2 is actually built on top of Blob Storage. | Unlimited | Forever | Hot: $0.018/GB, Cool: $0.01/GB | Hot: $0.004 per 10K read ops |
| **Azure Files** | Cloud file share that acts like a network drive you can mount. Great for sharing files between VMs. Not ideal for analytics pipelines. | 100TB per share | Forever | Standard: $0.06/GB, Premium: $0.30/GB | Included in storage cost |
| **Azure SQL Database** | Relational database. Could store JSONL as raw text but that is wasteful and defeats the purpose of a database. | 32GB to 4TB | Forever | $0.115/GB/month on top of fixed cost | Fixed cost regardless of access |
| **Azure Table Storage** | NoSQL key-value store. Very cheap but limited querying. Not great for nested JSON analytics. | 500TB | Forever | $0.045 per 10GB/month = $0.0045/GB | $0.00036 per 10K transactions |

### Storage Tier Explanation (applies to Blob/ADLS)

| Tier | Access Speed | Cost per GB/month | Best For |
|---|---|---|---|
| **Hot** | Instant | $0.023/GB | Data you read frequently |
| **Cool** | Instant | $0.010/GB | Data accessed once a month |
| **Archive** | Hours (rehydration needed) | $0.002/GB | Old data you rarely touch |

### We Choose: Azure Data Lake Storage Gen2 (ADLS Gen2)

**Why:**
- Designed exactly for this use case: storing raw analytics files (JSONL, CSV, Parquet)
- Hierarchical folders means we can organize cleanly:
  ```
  llmaven-raw/
  ├── 2026/
  │   ├── 01/
  │   │   ├── litellm_spend_logs_2026-01-01.jsonl
  │   │   └── litellm_spend_logs_2026-01-02.jsonl
  │   └── 02/
  │       └── ...
  ```
- Works natively with Azure Data Factory, Synapse, Databricks: no connectors needed
- Same price as Blob Storage but far more powerful for analytics
- Start with Hot tier. Our dataset is tiny (a few MB/day)

**Cost estimate for our use case:**
- ~1MB of JSONL per day = ~365MB/year = ~0.365GB
- $0.023/GB/month x 0.365GB = **$0.008/month (less than 1 cent)**

---

## STAGE 3: Processing (Cleaning Messy JSONL into Clean Rows)

> **Goal:** Take nested messy JSONL and flatten it into clean tables where one row equals one AI interaction

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

| Resource | What It Does | Scale | Cost per hour | Cost per GB processed |
|---|---|---|---|---|
| **Azure Functions** | Runs a Python script that reads JSONL, flattens it with pandas, writes clean Parquet back to Data Lake | Up to 1M executions free/month | ~$0.000016/GB-second of memory | Free for our data size |
| **Azure Data Factory Data Flows** | Visual drag-and-drop data transformation tool inside ADF. No code needed but limited flexibility for deeply nested JSON. | Unlimited | ~$0.228/hour of compute regardless of data size | $0.228/hour whether processing 1KB or 1TB |
| **Azure Databricks** | Apache Spark-based big data processing. Handles TB-scale transformations. Overkill for our data size. | Unlimited | ~$0.40/hour per node regardless of data size | $0.40/hour whether processing 1KB or 1TB |
| **Azure Synapse Analytics** | Combined data warehouse + Spark processing. Enterprise scale. Way too big for us. | Unlimited | ~$5/hour fixed + $5/TB for Serverless SQL queries | $5/TB scanned for Serverless SQL only |
| **Azure HDInsight** | Managed Hadoop/Spark clusters. Old, being deprecated. Avoid. | Unlimited | ~$0.50/hour per node | $0.50/hour regardless of data size |

### We Choose: Azure Functions (again)

**Why:**
- We are flattening a few thousand JSON records. This is a 5-second Python script, not a big data problem.
- The same Azure Function that does ingestion can do the cleaning in the same run:
  ```
  Extract JSONL -> clean it with pandas -> save clean Parquet to Data Lake
  ```
- Free, fast, simple.
- If data ever grows to millions of records, we can swap to Databricks later.

**The cleaning script:**
```python
import pandas as pd, json, collections

records = [json.loads(line) for line in open('raw.jsonl')]

# Count total requests per session (this is turns)
# We cannot use len(proxy_server_request.messages) because each new message
# resends the entire conversation history. So message count != turn count.
# Instead: group by session_id and count how many separate requests share it.
session_counts = collections.Counter(r['session_id'] for r in records)

clean = [{
    'date':              r['startTime'],
    'session_id':        r['session_id'],
    'user':              r['user'],
    'model':             r['model'],
    'prompt_tokens':     r['prompt_tokens'],
    'completion_tokens': r['completion_tokens'],
    'cost':              r['spend'],
    'turns':             session_counts[r['session_id']],  # total requests in this session
    'source':            str(r['request_tags'])
} for r in records]

pd.DataFrame(clean).to_parquet('clean.parquet')
```

**Why not `len(proxy_server_request.messages)` for turns?**

Because each new message in a conversation resends the entire history. So on turn 3, the messages list already contains turns 1 and 2 as well. `len(messages)` keeps growing and does not tell you which turn number you are on. The correct approach is to group all records by `session_id` and count how many separate requests share that session.

---

## STAGE 4: Analytical Storage (Clean Data for Querying)

> **Goal:** Store clean data somewhere fast and queryable so the dashboard can read it

| Resource | What It Does | Storage | Storage Cost per GB/month | Query Cost per GB scanned | Fixed Monthly Cost | Query Language |
|---|---|---|---|---|---|---|
| **Azure Synapse Analytics (Serverless SQL)** | Query Parquet files directly from Data Lake using SQL. No database needed. Pay per query, not per hour. | Reads from Data Lake (unlimited) | $0.023/GB (Data Lake rate) | $5 per TB = $0.000005/GB | $0 | SQL |
| **Azure SQL Database** | Traditional relational database. Load clean Parquet into tables. Always-on server. | 32GB to 4TB | $0.115/GB/month | Included in fixed cost | ~$15/month minimum even when idle | SQL |
| **Azure Cosmos DB** | NoSQL document database. Good for JSON but expensive and complex for analytics. | Unlimited | $0.25/GB/month | $0.008 per RU (varies by query complexity) | ~$25/month minimum | SQL-like |
| **Azure Data Explorer (Kusto)** | Time-series and log analytics database. Very fast for time-based queries. Complex to set up. | Unlimited | $0.033/GB/month compressed | Included in compute cost | ~$0.005/hour = ~$3.60/month minimum | KQL (different language) |
| **Azure Managed PostgreSQL** | Fully managed PostgreSQL. Familiar and powerful. Overkill since we already have clean Parquet files. | 32GB to 16TB | $0.115/GB/month | Included in fixed cost | ~$25/month minimum | SQL |
| **Parquet files in Data Lake (no DB)** | Keep clean Parquet in Data Lake. Synapse Serverless SQL queries them directly. No separate database needed. | Unlimited | $0.023/GB/month | $5 per TB = $0.000005/GB | $0 | SQL via Synapse |

### We Choose: Parquet files in Data Lake + Synapse Serverless SQL

**Why:**
- We do not need a separate database at all. Synapse can query Parquet files directly with SQL.
- No always-on server means no minimum monthly cost.
- Pay only when someone runs a query. Our tiny dataset costs fractions of a penny per query.
- Parquet is a columnar format: much faster and smaller than CSV for analytics:
  ```
  CSV 100MB -> Parquet ~15MB (85% smaller, 10x faster to query)
  ```
  This is because Parquet uses dictionary encoding. A value like "claude-sonnet-4-6" that repeats 12,000 times is stored once in a dictionary, then referenced by a small integer for each row.
- Azure SQL Database at $15/month is wasteful when Synapse Serverless is essentially free at our scale.

**Cost breakdown for our actual data:**

| Scenario | Data Size | Storage cost/month | Query cost per query | Query cost at 100 queries/day |
|---|---|---|---|---|
| Our demo (test records) | 2KB Parquet | $0.000000046/month | $0.00000001 | $0.00/month |
| Real data (13k sessions) | 4MB Parquet | $0.000092/month | $0.00002 | $0.06/month |
| 1 year projected | 15MB Parquet | $0.00035/month | $0.000075 | $0.23/month |

**Final storage structure in Data Lake:**
```
llmaven/
├── raw/                          <- Stage 2: raw JSONL
│   └── 2026/01/01/logs.jsonl
└── clean/                        <- Stage 4: clean Parquet
    └── 2026/01/01/clean.parquet
```

---

## STAGE 5: Dashboard (Visualization)

> **Goal:** Show charts covering cost over time, model usage, tokens, and session turns

| Resource | What It Does | Data Sources | Cost per month | Cost per user | Cost per GB |
|---|---|---|---|---|---|
| **Power BI** | Microsoft's enterprise dashboard tool. Connects natively to all Azure services. Drag-and-drop charts. Shareable links. | Azure Synapse, Data Lake, SQL | Free (Desktop, local only) / ~$10/user/month (Pro for sharing) | $0 Desktop / $10 Pro | Free: query cost happens at Synapse layer ($5/TB) |
| **Azure Managed Grafana** | Open-source Grafana hosted by Azure. Better for time-series dashboards. More technical to set up. | Synapse, SQL, Prometheus | ~$9/month flat (unlimited users included) | $0 extra: unlimited users included | Free: query cost at Synapse layer ($5/TB) |
| **Azure Static Web App + Plotly/Dash** | Custom Python dashboard. Full control over every chart and layout. More development work. | Anything: Parquet, SQL, APIs | Free hosting (Static Web App free tier) | $0 | $0 hosting: query cost at Synapse layer |
| **Streamlit on Azure Container Apps** | Python dashboard framework. Fastest to build. Host as a container. Scales to zero when not in use. | Parquet, SQL, anything Python can read | ~$2 to $5/month (scales to zero when idle) | $0 extra per user | Container cost is compute-based (vCPU/RAM), not data-size-based. Larger data needs more RAM: 4MB needs 0.5GB RAM, 1GB data needs 4GB RAM |
| **Jupyter Notebooks (Azure ML)** | Not really a dashboard. Better for one-time exploration. Not shareable as a live dashboard. | Anything | Free tier / ~$0 to $5/month depending on compute | Not multi-user | $0 |

### Container Apps cost vs data size

Since Container Apps charges for compute (vCPU + RAM) not data size, larger data indirectly increases cost because it needs more RAM to process:

| Parquet Size | RAM Needed | Container Size | Cost/month |
|---|---|---|---|
| 4MB (our demo) | 512MB RAM | 0.25 vCPU / 0.5GB | ~$2 to $3/month |
| 100MB (1 year data) | 1GB RAM | 0.5 vCPU / 1GB | ~$5/month |
| 1GB (multi-year) | 4GB RAM | 1 vCPU / 4GB | ~$15/month |

### We Choose: Streamlit on Azure Container Apps

**Why:**
- Streamlit turns a Python script into a web dashboard in about 20 lines of code
- No drag-and-drop limitations: full flexibility for custom charts
- Azure Container Apps is serverless: scales to zero when nobody is looking at it (free when idle)
- Power BI Pro requires ~$10/user/month to share with the team
- Grafana is better suited for real-time metrics, not batch analytics

**What the dashboard shows:**
```
+------------------------------------------+
|  LLMaven Usage Dashboard                 |
+---------------+--------------------------+
| Model Usage   | Claude 94% / Others 6%   |
| Cost/Day      | Line chart over time     |
| Tokens        | Input vs Output bar chart|
| Sessions      | Turns distribution       |
| Top Users     | By spend / by calls      |
+---------------+--------------------------+
```

---

## Full Architecture Summary

```
+-------------------------------------------------------+
| LLMaven Server (LiteLLM + PostgreSQL)                 |
+------------------------+------------------------------+
                         | llmaven infra extract (daily)
                         v
+-------------------------------------------------------+
| STAGE 1: Azure Functions (Ingestion + Processing)     |
| - Runs daily at midnight (cron trigger)               |
| - Calls llmaven extract -> gets JSONL                 |
| - Cleans JSONL -> Parquet with pandas                 |
| - Uploads both raw + clean to Data Lake               |
+------------------------+------------------------------+
                         |
                         v
+-------------------------------------------------------+
| STAGE 2+4: Azure Data Lake Storage Gen2               |
| llmaven/                                              |
| +-- raw/2026/01/01/logs.jsonl    <- raw files         |
| +-- clean/2026/01/01/clean.parquet <- clean files     |
+------------------------+------------------------------+
                         | SQL queries via Synapse Serverless
                         v
+-------------------------------------------------------+
| STAGE 5: Streamlit Dashboard (Azure Container Apps)   |
| - Reads Parquet from Data Lake                        |
| - Shows: model usage, cost, tokens, sessions          |
| - Shareable URL for the whole team                    |
+-------------------------------------------------------+
```

---

## Total Cost Estimate (Monthly)

| Component | Resource | Data Size | Cost per GB | Estimated Monthly Cost |
|---|---|---|---|---|
| Ingestion + Processing | Azure Functions | ~1MB/day new data | Free tier | $0.00 |
| Raw Storage | ADLS Gen2 Hot tier | ~365MB/year cumulative | $0.023/GB | ~$0.008/month |
| Clean Storage | ADLS Gen2 Hot tier | ~55MB/year (Parquet compressed) | $0.023/GB | ~$0.001/month |
| Querying | Synapse Serverless SQL | 4MB scanned per query | $5/TB ($0.000005/GB) | ~$0.06/month at 100 queries/day |
| Dashboard | Container Apps (scales to zero) | 4MB Parquet needs 0.5GB RAM | $0.000012/vCPU-second | ~$2 to $5/month |
| **TOTAL** | | | | **~$2 to $5/month** |

**Compared to a naive approach:**
- Azure SQL Database always-on: ~$15/month minimum regardless of data size
- Power BI Pro for 5 users: ~$50/month
- Azure Databricks: ~$100/month minimum

**Saving ~$160/month by choosing the right tools for the actual scale of this project.**

---

## What We Would Change If Data Grew 100x

| Stage | Current Choice | Why We Chose It | If Data Grew to 100x |
|---|---|---|---|
| Ingestion | Azure Functions | Free, simple, 30 runs/month | Azure Data Factory (handles complex orchestration) |
| Processing | Azure Functions + pandas | 5-second Python script | Azure Databricks (parallel Spark processing) |
| Storage | ADLS Gen2 Hot | Tiny data, frequent access | ADLS Gen2 Cool (cheaper for large infrequently accessed volumes) |
| Querying | Synapse Serverless | Pay per query, near zero cost | Synapse Dedicated Pool (faster for constant heavy queries) |
| Dashboard | Streamlit | Fast to build, scales to zero | Power BI (better enterprise features for large orgs) |
