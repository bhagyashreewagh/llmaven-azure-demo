# LLMaven Azure Pipeline Demo

A lightweight Azure data pipeline that extracts AI usage logs from [LLMaven](https://github.com/uw-ssec/llmaven), stores them in Azure Data Lake, and displays them in a Streamlit dashboard.

---

## Architecture

```
LLMaven Server (LiteLLM + PostgreSQL)
        |
        v  daily at midnight
+------------------------------------------+
|  Azure Function (Ingestion + Processing) |
|  - calls llmaven extract -> JSONL        |
|  - cleans JSONL -> Parquet with pandas   |
+------------------+-----------------------+
                   |
                   v
+------------------------------------------+
|  Azure Data Lake Storage Gen2            |
|  raw/YYYY/MM/DD/logs.jsonl               |
|  clean/YYYY/MM/DD/clean.parquet          |
+------------------+-----------------------+
                   |
                   v
+------------------------------------------+
|  Streamlit Dashboard (Container Apps)    |
|  - model usage, cost, tokens, sessions  |
|  - filter by source, turns, model       |
+------------------------------------------+
```

---

## Repo Structure

```
|- pulumi/                     # Infrastructure as Code (Pulumi Python)
|   |- __main__.py             # All Azure resources defined here
|   |- Pulumi.yaml
|   |- Pulumi.dev.yaml         # Stack config (location, LLMaven URL/key)
|   +- requirements.txt
|
|- function_app/               # Azure Function - daily pipeline
|   |- extract_pipeline/
|   |   +- __init__.py         # Timer trigger: extract -> clean -> upload
|   |- host.json
|   +- requirements.txt
|
|- dashboard/                  # Streamlit dashboard
|   |- app.py                  # All charts + filtering
|   |- Dockerfile
|   +- requirements.txt
|
|- test-extract-output/        # Sample JSONL from local LLMaven run
|   +- litellm_spend_logs_*.jsonl
|
+- azure_pipeline_resources.md # Resource comparison + cost estimates
```

---

## Azure Resources Used

| Stage | Resource | Why |
|---|---|---|
| Ingestion + Processing | Azure Functions (Consumption Y1) | Free tier, runs Python on schedule, no server |
| Raw Storage | Azure Data Lake Storage Gen2 | Hierarchical folders, built for analytics, ~$0.01/month |
| Clean Storage | ADLS Gen2 (Parquet) | 85% smaller than CSV, 10x faster queries |
| Dashboard | Azure Container Apps (scale-to-zero) | Free when idle, shareable URL |

**Estimated monthly cost: ~$2-5/month**

See [azure_pipeline_resources.md](./azure_pipeline_resources.md) for full resource comparison and alternatives considered.

---

## Deploy

### Prerequisites
- [Pulumi CLI](https://www.pulumi.com/docs/install/)
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) + logged in (`az login`)
- Python 3.11+

### 1. Deploy infrastructure

```bash
cd pulumi
pip install -r requirements.txt
pulumi stack init dev
pulumi config set azure-native:location westus2
pulumi config set llmaven_url "https://your-llmaven-server"
pulumi config set --secret llmaven_api_key "sk-your-key"
pulumi up
```

### 2. Build + push dashboard image

```bash
cd dashboard
docker build -t ghcr.io/<your-username>/llmaven-dashboard:latest .
docker push ghcr.io/<your-username>/llmaven-dashboard:latest
```

### 3. Run dashboard locally (no Azure needed -- uses demo data)

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

---

## Dashboard Features

- **Model usage** -- pie chart of which AI models are used
- **Daily cost** -- area chart of spend over time
- **Token distribution** -- input vs output tokens per session
- **Turns per session** -- histogram of conversation length
- **Source filter** -- filter by Claude-Code / SafeMind / curl
- **Top users by cost** -- who is spending the most
- **Raw records table** -- filterable clean data table
