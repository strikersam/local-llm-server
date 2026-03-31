# Langfuse Observability Guide

Langfuse is the observability layer for qwen-server. Every authenticated chat request is traced with request/response content, token counts, latency, infrastructure cost, and commercial API savings estimates.

---

## Setup

### 1. Create a Langfuse project

- **Cloud:** Create a free account at [cloud.langfuse.com](https://cloud.langfuse.com), create a project, and generate API keys under Settings → API Keys.
- **Self-hosted:** Deploy Langfuse via Docker and use your instance URL.

### 2. Configure credentials

```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

`LANGFUSE_HOST` is accepted as an alias for `LANGFUSE_BASE_URL`.

### 3. Optional tuning

```env
# Force REST ingestion instead of the Python SDK (useful if SDK has SSL issues)
LANGFUSE_USE_HTTP_ONLY=true

# Flush SDK events more aggressively (smaller batches, lower latency)
LANGFUSE_FLUSH_AT=1
```

### 4. Verify the connection

From the browser admin UI:
- Go to `http://localhost:8000/admin/ui/`
- Scroll to the **Langfuse diagnostic** section
- Click **Run connection test**

Or check proxy startup logs:

```
[INFO] Langfuse connection: OK (project: My Project)
```

After sending a chat request, a trace should appear in the Langfuse dashboard within a few seconds.

---

## What Gets Traced

Every authenticated request to `/v1/chat/completions`, `/api/chat`, and `/v1/messages` creates a trace in Langfuse.

### Trace structure

```
Trace
├── name:     "chat-completion"
├── user_id:  alice@company.com     ← from the key's email field
├── tags:     ["dept:engineering"]  ← from the key's department field
└── metadata:
    ├── department:    "engineering"
    └── local_model:   "qwen3-coder:30b"

    └── Generation
        ├── name:    "chat completion"
        ├── model:   "qwen3-coder:30b"
        ├── input:   [messages array, truncated to 48KB]
        ├── output:  "response text"
        ├── usage:
        │   ├── input_tokens:   523
        │   ├── output_tokens:  142
        │   └── total_tokens:   665
        └── metadata:
            ├── estimated_commercial_equivalent_usd:  0.00247
            ├── estimated_savings_vs_commercial_usd:  0.00241
            ├── commercial_reference_model:           "Claude Sonnet 4.6 / GPT-4.1 class (reference)"
            ├── latency_ms:                           3820
            ├── ttft_ms:                              410
            ├── tokens_per_sec:                       37.2
            ├── infra_electricity_usd:                0.0000059
            ├── infra_hardware_usd:                   0.0000019
            ├── infra_energy_kwh:                     0.0000000491
            └── key_id:                               "kid_abc123"
```

### Legacy API_KEYS traces

If a request is authenticated via the legacy `API_KEYS` env var (rather than `KEYS_FILE`), it appears in Langfuse as:
- `user_id = "unknown"`
- `department = "legacy"`
- No `key_id`

Switch to `KEYS_FILE` to get full per-user observability.

---

## Metadata Fields Explained

### Performance metrics

| Field | What it measures | Unit |
|-------|-----------------|------|
| `latency_ms` | Total request duration (first byte of request → last byte of response) | milliseconds |
| `ttft_ms` | Time to first token — how long before streaming starts | milliseconds |
| `tokens_per_sec` | Output throughput (output_tokens / latency in seconds) | tokens/second |

**How to read them:**
- `ttft_ms` of 0 means non-streaming request (counted all at once)
- `tokens_per_sec` of 0 means latency was too short to calculate or was a cached/empty response
- High `latency_ms` with low `tokens_per_sec` usually means the model is memory-mapped (running from NVMe), not fully in RAM

### Commercial savings metrics

| Field | What it measures |
|-------|-----------------|
| `estimated_commercial_equivalent_usd` | What this request would cost using the reference commercial API |
| `estimated_savings_vs_commercial_usd` | `commercial_equivalent_usd` minus your actual infra cost for this request |
| `commercial_reference_model` | The reference API being compared against (e.g. "Claude Sonnet 4.6 / GPT-4.1 class") |

**Example interpretation:**
- `estimated_commercial_equivalent_usd = 0.0025` → This request would have cost $0.0025 on Claude Sonnet 4.6
- `estimated_savings_vs_commercial_usd = 0.0024` → You actually paid ~$0.0001 in electricity+hardware, saving $0.0024

**Caveats:**
- The commercial reference price is a static value from `commercial_equivalent.py` — it does not update automatically when vendors change pricing
- "Savings" includes infrastructure cost as the denominator; if `INFRA_*` values are not configured, the cost is assumed to be $0 (overestimates savings)
- The comparison is to the *closest equivalent* commercial model — not necessarily the exact model you'd use

### Infrastructure cost metrics

| Field | What it measures |
|-------|-----------------|
| `infra_electricity_usd` | Electricity cost for this request (wattage × latency × electricity rate) |
| `infra_hardware_usd` | Hardware amortization allocated to this request (hardware cost / amortization months / active hours) |
| `infra_energy_kwh` | Kilowatt-hours consumed (total watts × latency in hours) |

**How the calculation works:**

```
total_watts = INFRA_GPU_ACTIVE_WATTS + INFRA_SYSTEM_WATTS
latency_hours = latency_ms / 3_600_000
energy_kwh = total_watts * latency_hours / 1000
electricity_usd = energy_kwh * INFRA_ELECTRICITY_USD_KWH

hardware_cost_per_request = INFRA_HARDWARE_COST_USD
                          / (INFRA_AMORTIZATION_MONTHS * 30 * 24 * 3600 * 1000)
                          * latency_ms
```

**Example (Intel AI PC, 3.8-second response):**

```
total_watts = 150 + 50 = 200W
latency_hours = 3820 / 3_600_000 = 0.001061 h
energy_kwh = 200 * 0.001061 / 1000 = 0.000000212 kWh

Wait — this is a 200W system for 3.82 seconds:
energy_kwh = (200W × 3.82s) / 3_600_000 = 0.000212 Wh = 0.000000212 kWh
electricity_usd = 0.000000212 * 0.12 = $0.0000000254 per request

hardware_cost_per_request (over 36 months):
= $2000 / (36 * 30 * 24 * 3600 * 1000 ms) * 3820 ms
= $2000 / (93,312,000,000 ms) * 3820
= $0.0000000820 per request
```

These numbers are small per-request — they add up across thousands of requests per day, visible in Langfuse aggregate views.

---

## Reading Langfuse Dashboards

### Traces view

The main traces list shows every request. Useful columns:

- **User** — the key's email address
- **Tags** — `dept:engineering` etc. — filter by team
- **Latency** — request duration
- **Cost** — estimated commercial cost (shown in Langfuse's built-in cost tracking)

Click any trace to see:
1. The **Generation** record with full input/output (truncated at 48KB)
2. All metadata fields listed in the previous section
3. Token usage breakdown

### Filtering by department

Use the tag filter in Langfuse: `dept:engineering` shows all requests from that team.

Or filter by user email to see individual user activity.

### Cost dashboard

Langfuse's built-in cost view uses the `estimated_commercial_equivalent_usd` values emitted as generation `usage.unit` cost. In Langfuse → Costs:

- **Total cost over period** — aggregate commercial-equivalent cost
- **Cost by model** — breakdown by which local model was used
- **Cost by user** — per-user consumption

> Note: Because local inference is essentially free at the point of use, the "cost" here represents *what you would have paid* if using the equivalent commercial API — not what you actually spent on electricity.

### Performance trends

In Langfuse → Traces → filter by model → look at `latency_ms` and `tokens_per_sec` metadata:

- Consistent `tokens_per_sec` above 20 = model is in RAM
- `tokens_per_sec` below 5 = model is memory-mapped from NVMe
- Spiky `ttft_ms` = model is being evicted and reloaded between requests

---

## Customising Commercial Reference Prices

The default pricing map covers the models in this repo. To add custom prices or override defaults:

### Inline JSON (single model)

```env
COMMERCIAL_EQUIVALENT_PRICES_JSON={"my-custom-model:tag":{"commercial_name":"GPT-4.1","input_per_million_usd":2,"output_per_million_usd":8}}
```

### JSON file (multiple overrides)

```env
COMMERCIAL_EQUIVALENT_PRICES_FILE=pricing.json
```

Format of `pricing.json`:

```json
{
  "qwen3-coder:30b": {
    "commercial_name": "Claude Sonnet 4.6 / GPT-4.1 class",
    "input_per_million_usd": 3.0,
    "output_per_million_usd": 15.0
  },
  "my-local-model:tag": {
    "commercial_name": "GPT-4.1-mini",
    "input_per_million_usd": 0.40,
    "output_per_million_usd": 1.60
  }
}
```

The inline JSON and file overrides are merged on top of the built-in defaults. Keys not present in overrides keep their default values.

---

## What is NOT Traced

| What | Why |
|------|-----|
| Admin API requests | Not chat requests — no model involved |
| Health check (`/health`) | Unauthenticated, no model |
| Agent internal sub-calls | Agent loops call the proxy which emits traces for each step |
| Oversized messages | Messages >48KB are truncated in the trace payload (token counts are accurate) |
| Requests with no Langfuse keys | Silently skipped — no error |

---

## Instrumentation Gaps and Recommendations

The current implementation is solid but has a few gaps worth noting:

### Gap 1: Infrastructure cost at model-idle time

The current model attributes idle GPU power (`INFRA_GPU_IDLE_WATTS`) to requests pro-rata. Idle cost while the server is running but receiving no requests is not tracked in Langfuse.

**Recommendation:** Add a periodic Langfuse event (e.g. every 5 minutes) for baseline idle cost using the existing `infra_cost.py` module.

### Gap 2: No per-session cost rollup

Individual requests are traced, but there's no Langfuse session grouping that aggregates cost across all requests in a single agent run or user session.

**Recommendation:** When agent sessions make multiple requests, use the same Langfuse `trace_id` or `session_id` for all of them to enable rollup.

### Gap 3: Cloud-proxy models (`:cloud` tags) cost

When using `deepseek-v3.2:cloud`, `minimax-m2.7:cloud`, or `glm-5:cloud`, actual API costs are charged to the vendor — but the proxy records these as local infrastructure cost (near-zero). The `commercial_reference_model` field is set correctly, but `infra_electricity_usd` will understate true cost.

**Recommendation:** Detect `:cloud` model tags and use the full commercial cost as the "actual" cost rather than electricity+hardware in those cases.

### Gap 4: No Langfuse dashboard for model download costs

Model storage costs (`INFRA_MODEL_STORAGE_GB`, `INFRA_STORAGE_USD_GB_MO`) are configured but not currently emitted per-request to Langfuse.

**Recommendation:** Include `infra_storage_usd` as a separate metadata field, calculated as `model_storage_gb * storage_cost_per_gb_per_month / (30 * 24 * 60)` per request-minute.

---

## Screenshots

> **Note:** No Langfuse screenshots are currently committed to the repository.
> The following describes expected Langfuse views.

### Missing screenshots to capture

1. **Traces list view** — showing multiple requests with user_id and latency columns
2. **Single trace detail** — expanded Generation record showing all metadata fields
3. **Cost dashboard** — Langfuse cost aggregation over time by model
4. **Department tag filter** — traces filtered by `dept:engineering`
5. **Admin UI Langfuse diagnostic** — success and failure state

### Where to put screenshots

```
docs/screenshots/langfuse-traces-list.png
docs/screenshots/langfuse-trace-detail.png
docs/screenshots/langfuse-cost-dashboard.png
docs/screenshots/langfuse-department-filter.png
docs/screenshots/admin-langfuse-diagnostic-ok.png
docs/screenshots/admin-langfuse-diagnostic-fail.png
```
