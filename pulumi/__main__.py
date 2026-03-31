"""
LLMaven Azure Pipeline — Pulumi Infrastructure
================================================
Architecture (cheapest viable setup for our data scale):

  LLMaven Server
      │
      ▼
  Azure Function (timer: daily)
  ├── calls llmaven extract → gets JSONL
  ├── cleans JSONL → Parquet with pandas
  └── uploads both to Data Lake
      │
      ▼
  Azure Data Lake Storage Gen2
  ├── raw/YYYY/MM/DD/logs.jsonl
  └── clean/YYYY/MM/DD/clean.parquet
      │
      ▼
  Streamlit Dashboard (Azure Container Apps)
  └── reads Parquet → shows charts (cost, tokens, models, sessions)
"""

import pulumi
import pulumi_azure_native as azure_native
from pulumi_azure_native import storage, web, app, operationalinsights, resources

# ── Config ────────────────────────────────────────────────────────────────────
config = pulumi.Config()
location = config.get("location") or "westus2"
llmaven_url     = config.get("llmaven_url") or ""      # eScience's LLMaven URL
llmaven_api_key = config.get("llmaven_api_key") or ""  # eScience's master key

# ── Resource Group ─────────────────────────────────────────────────────────────
# A resource group is just a folder in Azure that holds all related resources.
# Deleting the resource group deletes everything inside it — easy cleanup.
resource_group = resources.ResourceGroup(
    "llmaven-rg",
    location=location,
    tags={"project": "llmaven", "env": "demo"},
)

# ── STAGE 2: Azure Data Lake Storage Gen2 ─────────────────────────────────────
# Why ADLS Gen2 over plain Blob Storage?
#   • is_hns_enabled=True gives us a real folder hierarchy (not flat buckets)
#   • Works natively with Synapse, Databricks, Azure ML — no extra connectors
#   • Same price as Blob Storage (~$0.018/GB/month on Hot tier)
#
# Alternatives considered:
#   • Azure Blob Storage       — no folder hierarchy, fine for simple use
#   • Azure SQL Database       — $15/month minimum, overkill for raw files
#   • Azure Table Storage      — too limited for nested JSON analytics
data_lake = storage.StorageAccount(
    "llmavendatalake",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=storage.SkuArgs(name=storage.SkuName.STANDARD_LRS),   # Locally redundant — cheapest, fine for demo
    kind=storage.Kind.STORAGE_V2,
    is_hns_enabled=True,   # ← This is what makes it ADLS Gen2 (not plain Blob)
    access_tier=storage.AccessTier.HOT,  # Hot tier: instant access, low cost at our tiny scale
    tags={"role": "data-lake"},
)

# Raw container — stores original JSONL files exactly as extracted from LLMaven
raw_container = storage.BlobContainer(
    "raw",
    resource_group_name=resource_group.name,
    account_name=data_lake.name,
    public_access=storage.PublicAccess.NONE,
)

# Clean container — stores processed Parquet files (flat rows, ready for dashboard)
clean_container = storage.BlobContainer(
    "clean",
    resource_group_name=resource_group.name,
    account_name=data_lake.name,
    public_access=storage.PublicAccess.NONE,
)

# Get the Data Lake connection string (used by Function App + Dashboard)
data_lake_keys = storage.list_storage_account_keys_output(
    resource_group_name=resource_group.name,
    account_name=data_lake.name,
)
data_lake_conn_str = pulumi.Output.all(data_lake.name, data_lake_keys).apply(
    lambda args: (
        f"DefaultEndpointsProtocol=https;"
        f"AccountName={args[0]};"
        f"AccountKey={args[1].keys[0].value};"
        f"EndpointSuffix=core.windows.net"
    )
)

# ── STAGE 1: Azure Function App (Ingestion + Processing) ──────────────────────
# Why Azure Functions over Azure Data Factory?
#   • ADF costs ~$1/1000 pipeline runs + compute — overkill for 30 runs/month
#   • Azure Functions: 1M free executions/month — we use ~30
#   • Our pipeline is just "run a Python script daily" — Functions are perfect for this
#   • No servers to manage, scales to zero automatically
#
# Alternatives considered:
#   • Azure Data Factory    — enterprise grade, expensive, complex for our use case
#   • Azure Logic Apps      — limited flexibility for custom Python code
#   • Azure Databricks      — $0.40+/hour, massive overkill for KB-sized data

# Functions need their own dedicated storage account (Azure requirement)
func_storage = storage.StorageAccount(
    "llmavenfuncstorage",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=storage.SkuArgs(name=storage.SkuName.STANDARD_LRS),
    kind=storage.Kind.STORAGE_V2,
    tags={"role": "function-storage"},
)

func_storage_keys = storage.list_storage_account_keys_output(
    resource_group_name=resource_group.name,
    account_name=func_storage.name,
)
func_storage_conn_str = pulumi.Output.all(func_storage.name, func_storage_keys).apply(
    lambda args: (
        f"DefaultEndpointsProtocol=https;"
        f"AccountName={args[0]};"
        f"AccountKey={args[1].keys[0].value};"
        f"EndpointSuffix=core.windows.net"
    )
)

# Consumption plan = serverless, pay per execution, scales to zero
# Y1/Dynamic = the free serverless tier (not a dedicated always-on server)
func_plan = web.AppServicePlan(
    "llmaven-func-plan",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=web.SkuDescriptionArgs(
        name="Y1",         # Y1 = consumption (serverless)
        tier="Dynamic",    # Dynamic = scales to zero, pay per use
    ),
    kind="functionapp",
)

# The Function App itself
# It runs our Python extract_pipeline function on a daily timer trigger
function_app = web.WebApp(
    "llmaven-func-app",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    server_farm_id=func_plan.id,
    kind="functionapp",
    site_config=web.SiteConfigArgs(
        python_version="3.11",
        app_settings=[
            # Required by Azure Functions runtime
            web.NameValuePairArgs(name="AzureWebJobsStorage",           value=func_storage_conn_str),
            web.NameValuePairArgs(name="FUNCTIONS_EXTENSION_VERSION",   value="~4"),
            web.NameValuePairArgs(name="FUNCTIONS_WORKER_RUNTIME",      value="python"),
            web.NameValuePairArgs(name="WEBSITE_RUN_FROM_PACKAGE",      value="1"),
            # Our pipeline config — set these once you have Layomi's credentials
            web.NameValuePairArgs(name="LLMAVEN_URL",                   value=llmaven_url),
            web.NameValuePairArgs(name="LLMAVEN_API_KEY",               value=llmaven_api_key),
            # Data Lake connection — where to upload extracted + cleaned files
            web.NameValuePairArgs(name="DATA_LAKE_CONN_STR",            value=data_lake_conn_str),
            web.NameValuePairArgs(name="RAW_CONTAINER",                 value="raw"),
            web.NameValuePairArgs(name="CLEAN_CONTAINER",               value="clean"),
        ],
    ),
    tags={"role": "pipeline"},
)

# ── STAGE 5: Dashboard — Streamlit on Azure Container Apps ────────────────────
# Why Streamlit on Container Apps over Power BI?
#   • Power BI Pro = $10/user/month just to share dashboards with team
#   • Streamlit: write Python → get a shareable web dashboard instantly
#   • Container Apps scale to zero (min_replicas=0) → free when nobody is watching
#   • Full control over charts, filtering, layout — no drag-and-drop limits
#
# Alternatives considered:
#   • Power BI              — great for large orgs, expensive per user for sharing
#   • Azure Managed Grafana — $9/month, better for real-time metrics not batch analytics
#   • Azure Static Web App  — needs separate backend API for data, more complex

# Log Analytics Workspace — required by Container Apps for logging
log_analytics = operationalinsights.Workspace(
    "llmaven-logs",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=operationalinsights.WorkspaceSkuArgs(name="PerGB2018"),
    retention_in_days=30,
    tags={"role": "logging"},
)

log_analytics_keys = operationalinsights.get_shared_keys_output(
    resource_group_name=resource_group.name,
    workspace_name=log_analytics.name,
)

# Container Apps Environment — the shared network/runtime for our containers
container_env = app.ManagedEnvironment(
    "llmaven-container-env",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    app_logs_configuration=app.AppLogsConfigurationArgs(
        destination="log-analytics",
        log_analytics_configuration=app.LogAnalyticsConfigurationArgs(
            customer_id=log_analytics.customer_id,
            shared_key=log_analytics_keys.primary_shared_key,
        ),
    ),
    tags={"role": "container-env"},
)

# Streamlit Dashboard Container App
# Image: we build and push this from dashboard/Dockerfile
# For demo: using a placeholder — replace with your actual image after building
dashboard = app.ContainerApp(
    "llmaven-dashboard",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    managed_environment_id=container_env.id,
    configuration=app.ConfigurationArgs(
        ingress=app.IngressArgs(
            external=True,       # Publicly accessible URL
            target_port=8501,    # Streamlit's default port
            transport="auto",
        ),
    ),
    template=app.TemplateArgs(
        containers=[
            app.ContainerArgs(
                name="dashboard",
                # Replace with your own image after: docker build + push to GHCR or ACR
                image="ghcr.io/bhagyashreewagh/llmaven-dashboard:latest",
                resources=app.ContainerResourcesArgs(
                    cpu=0.5,        # Half a CPU core — plenty for Streamlit
                    memory="1Gi",   # 1GB RAM
                ),
                env=[
                    app.EnvironmentVarArgs(
                        name="DATA_LAKE_CONN_STR",
                        value=data_lake_conn_str,
                    ),
                    app.EnvironmentVarArgs(
                        name="CLEAN_CONTAINER",
                        value="clean",
                    ),
                ],
            ),
        ],
        scale=app.ScaleArgs(
            min_replicas=0,   # ← Scales to zero when nobody is using it (free when idle)
            max_replicas=1,   # Max 1 instance — we don't need more for a small team dashboard
        ),
    ),
    tags={"role": "dashboard"},
)

# ── Outputs ───────────────────────────────────────────────────────────────────
# These get printed after `pulumi up` so you know where everything lives

pulumi.export("resource_group",        resource_group.name)
pulumi.export("data_lake_name",        data_lake.name)
pulumi.export("raw_container",         raw_container.name)
pulumi.export("clean_container",       clean_container.name)
pulumi.export("function_app_name",     function_app.name)
pulumi.export("function_app_url",      function_app.default_host_name.apply(
    lambda h: f"https://{h}"
))
pulumi.export("dashboard_url",         dashboard.latest_revision_fqdn.apply(
    lambda fqdn: f"https://{fqdn}"
))
