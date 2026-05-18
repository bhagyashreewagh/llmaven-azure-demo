# LLM Spend Intelligence Dashboard

An interactive analytics dashboard for LiteLLM proxy usage logs.
Built with Streamlit + Plotly. Covers spend, token usage, cache efficiency, session analytics, and a plain-English AI Q&A tab.

---

## What it shows

| Tab | What you get |
|---|---|
| Overview | KPI cards, daily spend trend, model split, requests by status |
| Cost Explorer | Treemap drill-down, box plots per model, monthly burn rate, Haiku what-if calculator |
| Time Intelligence | Calendar heatmap, hour-of-day, day-of-week, week-over-week |
| Users | Leaderboard with efficiency score, per-user deep dive |
| Cache | Cache savings banner, daily hit rate chart, per-user efficiency |
| Sessions | Turns histogram, cost vs. length scatter, latency distribution |
| Ask the Data | Plain-English Q&A powered by Claude (Anthropic API) |

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/bhagyashreewagh/llmaven-azure-demo.git
cd llmaven-azure-demo
git checkout uw-dashboard
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
DATA_ZIP=path/to/your/logs.zip
```

- `ANTHROPIC_API_KEY` is only needed if you want to use the **Ask the Data** tab.
- `DATA_ZIP` should point to a `.zip` archive containing one or more `*.jsonl` files in LiteLLM proxy log format. If you leave this unset the app looks for `data/logs.zip` inside the project directory.

### 4. Run the app

```bash
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

---

## Data format

Each line in the JSONL files should be a JSON object with the fields that LiteLLM writes to its spend logs, including:

```
request_id, model, status, spend, startTime, endTime,
total_tokens, prompt_tokens, completion_tokens, session_id,
metadata.user_api_key_alias, metadata.usage_object.*
```

The `data.py` module documents the exact fields it reads.

---

## Project structure

```
llmaven-dashboard/
├── app.py                      # Thin entry point: page config, sidebar, tab routing
├── config.py                   # Color palette, Plotly defaults, ZIP_PATH
├── styles.py                   # Global CSS injection + SVG illustrations
├── utils.py                    # Number formatters, HTML helpers, _style()
├── data.py                     # load_data() - parses the JSONL zip archive
├── tabs/
│   ├── overview.py
│   ├── cost_explorer.py
│   ├── time_intelligence.py
│   ├── users.py
│   ├── cache.py
│   ├── sessions.py
│   └── ask_the_data.py
├── requirements.txt
├── .env.example                # Copy to .env and fill in your keys
└── README.md
```

---

## Tech stack

- [Streamlit](https://streamlit.io/) for the web UI
- [Plotly](https://plotly.com/python/) for all charts
- [Pandas](https://pandas.pydata.org/) for data wrangling
- [Anthropic Python SDK](https://github.com/anthropic/anthropic-sdk-python) for the AI Q&A tab
- [python-dotenv](https://github.com/theskumar/python-dotenv) for portable environment variable loading
