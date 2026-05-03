"""Generate Langfuse and Telegram mockup screenshots for documentation."""
import asyncio
import os
import sys
import tempfile
import pathlib

sys.stdout.reconfigure(encoding="utf-8")

OUT = "docs/screenshots"

TRACES_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; }
body { background: #0f0f11; color: #e4e4e7; min-height: 100vh; }
.sidebar { position: fixed; left: 0; top: 0; width: 220px; height: 100vh; background: #18181b; border-right: 1px solid #27272a; padding: 16px 0; }
.sidebar-logo { padding: 0 16px 16px; font-weight: 700; font-size: 16px; color: #f4f4f5; border-bottom: 1px solid #27272a; margin-bottom: 8px; }
.sidebar-logo span { color: #22c55e; }
.nav-item { padding: 8px 16px; color: #a1a1aa; cursor: pointer; border-radius: 4px; margin: 2px 8px; }
.nav-item.active { background: #27272a; color: #f4f4f5; }
.main { margin-left: 220px; padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-title { font-size: 20px; font-weight: 600; color: #f4f4f5; }
.filter-bar { display: flex; gap: 8px; margin-bottom: 16px; align-items: center; }
.filter-input { background: #27272a; border: 1px solid #3f3f46; border-radius: 6px; padding: 6px 12px; color: #e4e4e7; width: 240px; }
.filter-tag { background: #27272a; border: 1px solid #3f3f46; border-radius: 6px; padding: 6px 12px; color: #a1a1aa; font-size: 12px; }
.filter-tag.active { background: #1e3a5f; border-color: #3b82f6; color: #93c5fd; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 600; color: #71717a; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #27272a; }
td { padding: 11px 12px; border-bottom: 1px solid #1f1f23; vertical-align: middle; }
tr:hover td { background: #18181b; }
.user-email { color: #e4e4e7; font-weight: 500; }
.user-dept { color: #71717a; font-size: 12px; margin-top: 2px; }
.latency { color: #86efac; }
.tokens { color: #a1a1aa; }
.cost { color: #fbbf24; font-weight: 500; }
.savings { color: #86efac; font-weight: 500; }
.model-tag { background: #1c1c28; border: 1px solid #3f3f46; border-radius: 4px; padding: 2px 7px; font-size: 11px; color: #c4b5fd; font-family: monospace; }
.trace-id { color: #52525b; font-size: 11px; font-family: monospace; }
.pagination { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; color: #71717a; font-size: 13px; }
.nav-btn { background: #27272a; border: 1px solid #3f3f46; border-radius: 6px; padding: 6px 14px; color: #a1a1aa; }
</style>
</head>
<body>
<div class="sidebar">
  <div class="sidebar-logo"><span>lang</span>fuse</div>
  <div class="nav-item active">Traces</div>
  <div class="nav-item">Sessions</div>
  <div class="nav-item">Generations</div>
  <div class="nav-item">Scores</div>
  <div class="nav-item">Datasets</div>
  <div class="nav-item">Costs</div>
  <div class="nav-item">Users</div>
  <div class="nav-item">Settings</div>
</div>
<div class="main">
  <div class="page-header">
    <div class="page-title">Traces <span style="color:#52525b;font-size:14px;font-weight:400;">1,842 total</span></div>
    <div style="color:#71717a;font-size:13px;">Project: Local LLM Server &nbsp;|&nbsp; Last 7 days</div>
  </div>
  <div class="filter-bar">
    <input class="filter-input" value="" placeholder="Search traces..." />
    <div class="filter-tag">Model</div>
    <div class="filter-tag active">dept:engineering</div>
    <div class="filter-tag">User</div>
    <div class="filter-tag">Date range: Last 7 days</div>
  </div>
  <table>
    <thead>
      <tr>
        <th>ID</th><th>User</th><th>Model</th><th>Tokens</th><th>Latency</th><th>Equiv. Cost</th><th>Savings</th><th>Time</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><span class="trace-id">trc_8f3k...</span></td>
        <td><div><span class="user-email">alice@company.com</span><div class="user-dept">dept:engineering</div></div></td>
        <td><span class="model-tag">qwen3-coder:30b</span></td>
        <td class="tokens">2,341 / 487</td>
        <td class="latency">4.2s</td>
        <td class="cost">$0.0084</td>
        <td class="savings">+$0.0082</td>
        <td style="color:#52525b;font-size:12px;">2 min ago</td>
      </tr>
      <tr>
        <td><span class="trace-id">trc_2m9p...</span></td>
        <td><div><span class="user-email">bob@company.com</span><div class="user-dept">dept:engineering</div></div></td>
        <td><span class="model-tag">deepseek-r1:32b</span></td>
        <td class="tokens">4,102 / 1,204</td>
        <td class="latency">12.8s</td>
        <td class="cost">$0.0048</td>
        <td class="savings">+$0.0046</td>
        <td style="color:#52525b;font-size:12px;">5 min ago</td>
      </tr>
      <tr>
        <td><span class="trace-id">trc_q7rx...</span></td>
        <td><div><span class="user-email">alice@company.com</span><div class="user-dept">dept:engineering</div></div></td>
        <td><span class="model-tag">qwen3-coder:30b</span></td>
        <td class="tokens">1,820 / 312</td>
        <td class="latency">3.1s</td>
        <td class="cost">$0.0062</td>
        <td class="savings">+$0.0060</td>
        <td style="color:#52525b;font-size:12px;">11 min ago</td>
      </tr>
      <tr>
        <td><span class="trace-id">trc_5n2c...</span></td>
        <td><div><span class="user-email">carol@company.com</span><div class="user-dept">dept:research</div></div></td>
        <td><span class="model-tag">deepseek-r1:32b</span></td>
        <td class="tokens">8,441 / 2,103</td>
        <td class="latency">28.4s</td>
        <td class="cost">$0.0097</td>
        <td class="savings">+$0.0093</td>
        <td style="color:#52525b;font-size:12px;">23 min ago</td>
      </tr>
      <tr>
        <td><span class="trace-id">trc_w1jm...</span></td>
        <td><div><span class="user-email">alice@company.com</span><div class="user-dept">dept:engineering</div></div></td>
        <td><span class="model-tag">qwen3-coder:30b</span></td>
        <td class="tokens">3,204 / 891</td>
        <td class="latency">8.7s</td>
        <td class="cost">$0.0144</td>
        <td class="savings">+$0.0141</td>
        <td style="color:#52525b;font-size:12px;">41 min ago</td>
      </tr>
      <tr>
        <td><span class="trace-id">trc_p8vz...</span></td>
        <td><div><span class="user-email">dave@company.com</span><div class="user-dept">dept:design</div></div></td>
        <td><span class="model-tag">qwen3-coder:30b</span></td>
        <td class="tokens">987 / 203</td>
        <td class="latency">2.4s</td>
        <td class="cost">$0.0033</td>
        <td class="savings">+$0.0032</td>
        <td style="color:#52525b;font-size:12px;">1 hr ago</td>
      </tr>
      <tr>
        <td><span class="trace-id">trc_k3xq...</span></td>
        <td><div><span class="user-email">bob@company.com</span><div class="user-dept">dept:engineering</div></div></td>
        <td><span class="model-tag">deepseek-r1:671b</span></td>
        <td class="tokens">12,401 / 3,892</td>
        <td class="latency">94.1s</td>
        <td class="cost">$0.0181</td>
        <td class="savings">+$0.0178</td>
        <td style="color:#52525b;font-size:12px;">2 hr ago</td>
      </tr>
      <tr>
        <td><span class="trace-id">trc_y0bq...</span></td>
        <td><div><span class="user-email">carol@company.com</span><div class="user-dept">dept:research</div></div></td>
        <td><span class="model-tag">qwen3-coder:30b</span></td>
        <td class="tokens">2,801 / 644</td>
        <td class="latency">6.2s</td>
        <td class="cost">$0.0108</td>
        <td class="savings">+$0.0106</td>
        <td style="color:#52525b;font-size:12px;">3 hr ago</td>
      </tr>
    </tbody>
  </table>
  <div class="pagination">
    <div>Showing 1-8 of 1,842 traces</div>
    <div style="display:flex;gap:8px;">
      <button class="nav-btn">Previous</button>
      <button class="nav-btn">Next</button>
    </div>
  </div>
</div>
</body>
</html>"""

TRACE_DETAIL_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; }
body { background: #0f0f11; color: #e4e4e7; min-height: 100vh; }
.sidebar { position: fixed; left: 0; top: 0; width: 220px; height: 100vh; background: #18181b; border-right: 1px solid #27272a; padding: 16px 0; }
.sidebar-logo { padding: 0 16px 16px; font-weight: 700; font-size: 16px; color: #f4f4f5; border-bottom: 1px solid #27272a; margin-bottom: 8px; }
.sidebar-logo span { color: #22c55e; }
.main { margin-left: 220px; padding: 24px; }
.breadcrumb { color: #52525b; font-size: 13px; margin-bottom: 16px; }
.breadcrumb a { color: #3b82f6; text-decoration: none; }
.page-title { font-size: 18px; font-weight: 600; color: #f4f4f5; margin-bottom: 4px; }
.page-meta { color: #71717a; font-size: 12px; margin-bottom: 20px; font-family: monospace; }
.grid { display: grid; grid-template-columns: 1fr 320px; gap: 20px; }
.card { background: #18181b; border: 1px solid #27272a; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.card-title { font-size: 12px; font-weight: 600; color: #71717a; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }
.gen-bar { background: #3b82f6; height: 28px; border-radius: 4px; display: flex; align-items: center; padding: 0 10px; color: #fff; font-size: 12px; font-weight: 500; margin-bottom: 8px; }
.meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.meta-item { background: #0f0f11; border: 1px solid #27272a; border-radius: 6px; padding: 10px 12px; }
.meta-label { font-size: 11px; color: #52525b; margin-bottom: 4px; }
.meta-value { font-size: 14px; font-weight: 600; color: #e4e4e7; }
pre { background: #0f0f11; border: 1px solid #27272a; border-radius: 6px; padding: 12px; font-size: 11px; color: #a1a1aa; white-space: pre-wrap; word-break: break-word; font-family: monospace; max-height: 180px; overflow-y: auto; }
.tag { display: inline-block; background: #14532d; color: #86efac; border-radius: 9999px; padding: 2px 9px; font-size: 11px; margin: 2px; }
.stats-row { display: flex; gap: 16px; margin-bottom: 16px; }
.stat-box { background: #18181b; border: 1px solid #27272a; border-radius: 8px; padding: 12px 16px; flex: 1; }
.stat-label { font-size: 11px; color: #52525b; margin-bottom: 4px; }
.stat-value { font-size: 20px; font-weight: 700; color: #f4f4f5; }
.stat-sub { font-size: 11px; color: #71717a; margin-top: 2px; }
</style>
</head>
<body>
<div class="sidebar">
  <div class="sidebar-logo"><span>lang</span>fuse</div>
</div>
<div class="main">
  <div class="breadcrumb"><a href="#">Traces</a> / trc_2m9p4k8rq...</div>
  <div class="page-title">chat-completion</div>
  <div class="page-meta">trc_2m9p4k8rq7vz1nx &nbsp;|&nbsp; 2026-03-31 14:23:07 UTC &nbsp;|&nbsp; user: bob@company.com</div>

  <div class="stats-row">
    <div class="stat-box"><div class="stat-label">Total latency</div><div class="stat-value">12.8s</div><div class="stat-sub">ttft: 380ms</div></div>
    <div class="stat-box"><div class="stat-label">Tokens</div><div class="stat-value">5,306</div><div class="stat-sub">4,102 in / 1,204 out</div></div>
    <div class="stat-box"><div class="stat-label">Equiv. cost</div><div class="stat-value" style="color:#fbbf24;">$0.0048</div><div class="stat-sub">DeepSeek R1 API ref</div></div>
    <div class="stat-box"><div class="stat-label">Savings</div><div class="stat-value" style="color:#86efac;">$0.0046</div><div class="stat-sub">vs commercial API</div></div>
  </div>

  <div class="grid">
    <div>
      <div class="card">
        <div class="card-title">Timeline</div>
        <div style="color:#a1a1aa;font-size:12px;margin-bottom:8px;">chat completion &nbsp;<span style="color:#d8b4fe;background:#3b1f5e;padding:1px 6px;border-radius:4px;font-size:11px;">deepseek-r1:32b</span>&nbsp;&nbsp;<span style="color:#52525b;">12,820ms</span></div>
        <div class="gen-bar">Generation &nbsp;&nbsp; 4,102 in / 1,204 out &nbsp;&nbsp; 12.8s</div>
      </div>
      <div class="card">
        <div class="card-title">Input (truncated)</div>
        <pre>[
  {"role": "system", "content": "You are an expert software engineer..."},
  {"role": "user", "content": "Refactor the authentication middleware in proxy.py to use async context managers instead of try/finally blocks. Preserve all existing behavior including rate limiting and key validation..."}
]</pre>
      </div>
      <div class="card">
        <div class="card-title">Output</div>
        <pre>Here is the refactored authentication middleware using async context managers:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def authenticated_request(request: Request, key_store: KeyStore):
    key = extract_api_key(request)
    if not key:
        raise HTTPException(status_code=401, detail="Missing API key")
    record = await key_store.verify(key)
    if not record:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not await rate_limiter.check(record.key_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    try:
        yield record
    finally:
        pass
```

This approach is cleaner and ensures proper resource cleanup...</pre>
      </div>
    </div>
    <div>
      <div class="card">
        <div class="card-title">Metadata</div>
        <div class="meta-grid">
          <div class="meta-item"><div class="meta-label">department</div><div class="meta-value">engineering</div></div>
          <div class="meta-item"><div class="meta-label">local_model</div><div class="meta-value" style="color:#d8b4fe;font-size:11px;">deepseek-r1:32b</div></div>
          <div class="meta-item"><div class="meta-label">latency_ms</div><div class="meta-value">12,820</div></div>
          <div class="meta-item"><div class="meta-label">ttft_ms</div><div class="meta-value" style="color:#93c5fd;">380</div></div>
          <div class="meta-item"><div class="meta-label">tokens_per_sec</div><div class="meta-value">94.1</div></div>
          <div class="meta-item"><div class="meta-label">equiv_usd</div><div class="meta-value" style="color:#fbbf24;">$0.00481</div></div>
          <div class="meta-item"><div class="meta-label">savings_usd</div><div class="meta-value" style="color:#86efac;">$0.00462</div></div>
          <div class="meta-item"><div class="meta-label">elec_usd</div><div class="meta-value" style="font-size:11px;">$0.0000009</div></div>
          <div class="meta-item"><div class="meta-label">hw_usd</div><div class="meta-value" style="font-size:11px;">$0.0000003</div></div>
          <div class="meta-item"><div class="meta-label">energy_kwh</div><div class="meta-value" style="font-size:10px;">7.4e-9</div></div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">Tags</div>
        <span class="tag">dept:engineering</span>
      </div>
      <div class="card">
        <div class="card-title">Commercial reference</div>
        <div style="font-size:12px;color:#a1a1aa;">DeepSeek R1 API / Claude Opus 4.6 class</div>
        <div style="font-size:11px;color:#52525b;margin-top:6px;">Input: $0.55/M &nbsp;|&nbsp; Output: $2.19/M</div>
      </div>
    </div>
  </div>
</div>
</body>
</html>"""

COST_DASH_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; }
body { background: #0f0f11; color: #e4e4e7; }
.sidebar { position: fixed; left: 0; top: 0; width: 220px; height: 100vh; background: #18181b; border-right: 1px solid #27272a; padding: 16px 0; }
.sidebar-logo { padding: 0 16px 16px; font-weight: 700; font-size: 16px; color: #f4f4f5; border-bottom: 1px solid #27272a; margin-bottom: 8px; }
.sidebar-logo span { color: #22c55e; }
.nav-item { padding: 8px 16px; color: #a1a1aa; cursor: pointer; border-radius: 4px; margin: 2px 8px; }
.nav-item.active { background: #27272a; color: #f4f4f5; }
.main { margin-left: 220px; padding: 24px; }
.page-title { font-size: 20px; font-weight: 600; color: #f4f4f5; margin-bottom: 4px; }
.page-sub { color: #71717a; font-size: 13px; margin-bottom: 20px; }
.stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card { background: #18181b; border: 1px solid #27272a; border-radius: 8px; padding: 16px; }
.stat-label { font-size: 11px; color: #71717a; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 700; color: #f4f4f5; }
.stat-delta { font-size: 12px; color: #86efac; margin-top: 4px; }
.card { background: #18181b; border: 1px solid #27272a; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.card-title { font-size: 13px; font-weight: 600; color: #a1a1aa; margin-bottom: 16px; }
.bar-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.bar-label { width: 220px; font-size: 12px; color: #a1a1aa; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bar-wrap { flex: 1; background: #27272a; border-radius: 3px; height: 20px; overflow: hidden; }
.bar { height: 20px; border-radius: 3px; display: flex; align-items: center; padding-left: 8px; font-size: 11px; color: #fff; font-weight: 500; }
.bar-val { width: 70px; text-align: right; color: #fbbf24; font-size: 12px; font-weight: 500; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.donut-wrap { display: flex; flex-direction: column; align-items: center; padding: 8px 0; }
.donut { width: 160px; height: 160px; border-radius: 50%; background: conic-gradient(#3b82f6 0% 52%, #8b5cf6 52% 78%, #22c55e 78% 90%, #f59e0b 90% 100%); position: relative; }
.donut-hole { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); width: 90px; height: 90px; background: #18181b; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.legend { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; width: 200px; }
.legend-item { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #a1a1aa; }
.dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
</style>
</head>
<body>
<div class="sidebar">
  <div class="sidebar-logo"><span>lang</span>fuse</div>
  <div class="nav-item">Traces</div>
  <div class="nav-item">Sessions</div>
  <div class="nav-item">Generations</div>
  <div class="nav-item">Scores</div>
  <div class="nav-item">Datasets</div>
  <div class="nav-item active">Costs</div>
  <div class="nav-item">Users</div>
</div>
<div class="main">
  <div class="page-title">Cost Analysis</div>
  <div class="page-sub">Commercial-equivalent savings vs. running on cloud APIs &nbsp;|&nbsp; Last 30 days</div>

  <div class="stat-row">
    <div class="stat-card">
      <div class="stat-label">Equiv. API cost</div>
      <div class="stat-value">$12.84</div>
      <div class="stat-delta">What you would have paid</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Actual infra cost</div>
      <div class="stat-value">$0.19</div>
      <div class="stat-delta" style="color:#fbbf24;">Electricity + hardware</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Total savings</div>
      <div class="stat-value" style="color:#86efac;">$12.65</div>
      <div class="stat-delta">98.5% savings rate</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Total requests</div>
      <div class="stat-value">1,842</div>
      <div class="stat-delta">avg 61.4/day</div>
    </div>
  </div>

  <div class="grid2">
    <div class="card">
      <div class="card-title">Equiv. cost by model (30 days)</div>
      <div class="bar-row">
        <div class="bar-label">qwen3-coder:30b</div>
        <div class="bar-wrap"><div class="bar" style="width:100%;background:#3b82f6;">1,284 reqs</div></div>
        <div class="bar-val">$8.14</div>
      </div>
      <div class="bar-row">
        <div class="bar-label">deepseek-r1:32b</div>
        <div class="bar-wrap"><div class="bar" style="width:35%;background:#8b5cf6;">420 reqs</div></div>
        <div class="bar-val">$3.22</div>
      </div>
      <div class="bar-row">
        <div class="bar-label">deepseek-r1:671b</div>
        <div class="bar-wrap"><div class="bar" style="width:9%;background:#ec4899;">114 reqs</div></div>
        <div class="bar-val">$1.08</div>
      </div>
      <div class="bar-row">
        <div class="bar-label">frob/minimax-m2.5</div>
        <div class="bar-wrap"><div class="bar" style="width:2%;background:#22c55e;">24</div></div>
        <div class="bar-val">$0.40</div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Requests by department</div>
      <div class="donut-wrap">
        <div class="donut">
          <div class="donut-hole">
            <div style="font-size:18px;font-weight:700;color:#f4f4f5;">1,842</div>
            <div style="font-size:10px;color:#71717a;">requests</div>
          </div>
        </div>
        <div class="legend">
          <div class="legend-item"><div class="dot" style="background:#3b82f6;"></div>engineering &nbsp; 960 (52%)</div>
          <div class="legend-item"><div class="dot" style="background:#8b5cf6;"></div>research &nbsp; 480 (26%)</div>
          <div class="legend-item"><div class="dot" style="background:#22c55e;"></div>design &nbsp; 222 (12%)</div>
          <div class="legend-item"><div class="dot" style="background:#f59e0b;"></div>ops &nbsp; 180 (10%)</div>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Equiv. cost by user (top 5, 30 days)</div>
    <div class="bar-row">
      <div class="bar-label">alice@company.com</div>
      <div class="bar-wrap"><div class="bar" style="width:100%;background:#3b82f6;">612 reqs</div></div>
      <div class="bar-val">$4.82</div>
    </div>
    <div class="bar-row">
      <div class="bar-label">bob@company.com</div>
      <div class="bar-wrap"><div class="bar" style="width:64%;background:#8b5cf6;">348 reqs</div></div>
      <div class="bar-val">$3.14</div>
    </div>
    <div class="bar-row">
      <div class="bar-label">carol@company.com</div>
      <div class="bar-wrap"><div class="bar" style="width:48%;background:#22c55e;">240 reqs</div></div>
      <div class="bar-val">$2.41</div>
    </div>
    <div class="bar-row">
      <div class="bar-label">dave@company.com</div>
      <div class="bar-wrap"><div class="bar" style="width:31%;background:#f59e0b;">180 reqs</div></div>
      <div class="bar-val">$1.22</div>
    </div>
    <div class="bar-row">
      <div class="bar-label">eve@company.com</div>
      <div class="bar-wrap"><div class="bar" style="width:20%;background:#ec4899;">120 reqs</div></div>
      <div class="bar-val">$1.25</div>
    </div>
  </div>
</div>
</body>
</html>"""

TELEGRAM_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #17212b; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; color: #e4e4e7; display: flex; align-items: flex-start; justify-content: center; min-height: 100vh; padding: 20px; }
.chat { width: 380px; }
.chat-header { background: #232e3c; border-radius: 12px 12px 0 0; padding: 12px 16px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid #0d1117; }
.bot-avatar { width: 38px; height: 38px; border-radius: 50%; background: linear-gradient(135deg, #3b82f6, #8b5cf6); display: flex; align-items: center; justify-content: center; font-size: 18px; color: #fff; font-weight: 700; }
.bot-name { font-weight: 600; color: #f4f4f5; font-size: 15px; }
.bot-status { font-size: 12px; color: #4ade80; }
.messages { background: #17212b; padding: 12px; display: flex; flex-direction: column; gap: 8px; border-radius: 0 0 12px 12px; }
.msg { max-width: 85%; padding: 8px 12px; border-radius: 12px; font-size: 13px; line-height: 1.5; }
.msg.user { background: #2b5278; align-self: flex-end; border-bottom-right-radius: 4px; color: #e4e4e7; }
.msg.bot { background: #182533; align-self: flex-start; border-bottom-left-radius: 4px; color: #e4e4e7; }
.msg-time { font-size: 10px; color: #71717a; margin-top: 4px; text-align: right; }
.msg code { background: #0d1117; padding: 1px 5px; border-radius: 4px; font-family: monospace; font-size: 12px; color: #86efac; }
.msg pre { background: #0d1117; padding: 8px; border-radius: 6px; font-family: monospace; font-size: 11px; color: #a1a1aa; margin-top: 6px; white-space: pre; }
.status-row { display: flex; align-items: center; gap: 6px; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.green { background: #4ade80; }
.dot.red { background: #f87171; }
.dot.yellow { background: #fbbf24; }
</style>
</head>
<body>
<div class="chat">
  <div class="chat-header">
    <div class="bot-avatar">L</div>
    <div>
      <div class="bot-name">Local LLM Server</div>
      <div class="bot-status">online</div>
    </div>
  </div>
  <div class="messages">
    <div class="msg user">/status<div class="msg-time">14:23</div></div>
    <div class="msg bot">
      <strong>Server Status</strong><br><br>
      <div class="status-row"><div class="dot green"></div> Ollama: Running (PID 4780)</div>
      <div class="status-row"><div class="dot green"></div> Proxy: Running (PID 25084)</div>
      <div class="status-row"><div class="dot red"></div> Tunnel: Stopped</div>
      <br>
      <strong>Models loaded:</strong><br>
      &nbsp; qwen3-coder:30b &nbsp; deepseek-r1:32b
      <div class="msg-time">14:23</div>
    </div>
    <div class="msg user">/cost<div class="msg-time">14:24</div></div>
    <div class="msg bot">
      <strong>Infrastructure cost estimate</strong><br><br>
      GPU active: <code>40W</code> &nbsp; Idle: <code>8W</code><br>
      System: <code>25W</code> &nbsp; Rate: <code>$0.12/kWh</code><br><br>
      Projected (8h active/day):<br>
      &nbsp; Electricity: <code>~$0.021/day</code><br>
      &nbsp; Hardware: <code>~$1.85/day</code><br>
      &nbsp; Total: <code>~$1.87/day</code><br><br>
      Hardware cost $2000 over 36 months
      <div class="msg-time">14:24</div>
    </div>
    <div class="msg user">/models<div class="msg-time">14:25</div></div>
    <div class="msg bot">
      <strong>Loaded models:</strong><br><br>
      &nbsp; deepseek-r1:671b &nbsp;(404.0 GB)<br>
      &nbsp; deepseek-r1:32b &nbsp; (18.5 GB)<br>
      &nbsp; qwen3-coder:30b &nbsp;(17.3 GB)
      <div class="msg-time">14:25</div>
    </div>
    <div class="msg user">/restart tunnel<div class="msg-time">14:26</div></div>
    <div class="msg bot">
      Restarting tunnel...<br>
      Tunnel started. New URL:<br>
      <code>https://some-new-words.trycloudflare.com</code>
      <div class="msg-time">14:26</div>
    </div>
    <div class="msg user">/agent Fix the typo in README<div class="msg-time">14:27</div></div>
    <div class="msg bot">
      About to run agent task:<br>
      <em>"Fix the typo in README"</em><br><br>
      Reply <strong>yes</strong> within 30s to confirm, or ignore to cancel.
      <div class="msg-time">14:27</div>
    </div>
    <div class="msg user">yes<div class="msg-time">14:27</div></div>
    <div class="msg bot">
      Running agent... done.<br>
      Changed: <code>README.md</code>
      <div class="msg-time">14:27</div>
    </div>
  </div>
</div>
</body>
</html>"""


async def save_html_screenshot(html: str, name: str, pw, width: int = 1280, height: int = 900):
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        tmp_path = pathlib.Path(tmp.name)
    tmp.write_text(html, encoding="utf-8")
    browser = await pw.chromium.launch(headless=True)
    ctx = await browser.new_context(viewport={"width": width, "height": height})
    page = await ctx.new_page()
    url = "file:///" + str(tmp).replace("\\", "/")
    await page.goto(url)
    await page.wait_for_load_state("networkidle")
    await page.screenshot(path=f"{OUT}/{name}", full_page=True)
    await browser.close()
    tmp.unlink(missing_ok=True)
    print(f"saved {name}")


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        await save_html_screenshot(TRACES_HTML, "langfuse-traces-list.png", p)
        await save_html_screenshot(TRACE_DETAIL_HTML, "langfuse-trace-detail.png", p)
        await save_html_screenshot(COST_DASH_HTML, "langfuse-cost-dashboard.png", p)
        await save_html_screenshot(TELEGRAM_HTML, "telegram-bot-commands.png", p, width=480, height=900)


asyncio.run(main())
