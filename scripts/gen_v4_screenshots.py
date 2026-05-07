"""Generate v4 UI screenshots for the README using HTML mockups + system playwright CLI."""
from __future__ import annotations

import subprocess
import tempfile
import pathlib
import os

OUT = pathlib.Path("docs/screenshots/readme")
OUT.mkdir(parents=True, exist_ok=True)

# ── shared design tokens ─────────────────────────────────────────────────────

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#020304;color:#f7f9fc;font-family:'Manrope',system-ui,sans-serif;font-size:14px;line-height:1.5;}
:root{
  --bg-base:#020304;--bg-sidebar:#050608;--bg-surface:#0a0c0f;--bg-elevated:#111419;
  --bg-surface-2:#0e1116;--bg-surface-3:#151922;--bg-elevated-2:#1b2029;
  --text-primary:#f7f9fc;--text-secondary:#d9e0ea;--text-tertiary:#a8b3c2;--text-muted:#6e7786;
  --accent:#5da2ff;--accent-hover:#7ab1ff;--accent-soft:rgba(93,162,255,0.12);
  --danger:#ff6b7d;--warning:#ffbd66;--success:#46d9a4;--info:#7c9dff;
  --border:rgba(255,255,255,0.09);--border-soft:rgba(255,255,255,0.05);--border-strong:rgba(255,255,255,0.16);
  --radius-sm:14px;--radius:20px;--radius-lg:28px;
}
.layout{display:flex;min-height:100vh;}
/* Sidebar */
.sidebar{width:272px;min-height:100vh;background:var(--bg-sidebar);border-right:1px solid var(--border);
  display:flex;flex-direction:column;flex-shrink:0;padding:0;}
.sb-logo{display:flex;align-items:center;gap:10px;padding:20px 20px 16px;border-bottom:1px solid var(--border);}
.sb-logo-icon{width:32px;height:32px;border-radius:10px;background:linear-gradient(135deg,#1a3a6b,#0d2048);
  border:1px solid rgba(93,162,255,0.25);display:flex;align-items:center;justify-content:center;}
.sb-logo-icon svg{width:16px;height:16px;stroke:#5da2ff;fill:none;stroke-width:2;}
.sb-logo-text{flex:1;}
.sb-logo-name{font-size:13px;font-weight:700;color:var(--text-primary);letter-spacing:0.01em;}
.sb-logo-ver{font-size:10px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;letter-spacing:0.1em;}
.sb-nav{flex:1;padding:12px 8px;overflow-y:auto;}
.sb-section{font-size:9px;font-family:'IBM Plex Mono',monospace;font-weight:600;color:var(--text-muted);
  letter-spacing:0.18em;text-transform:uppercase;padding:14px 12px 6px;}
.sb-item{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:12px;
  color:var(--text-tertiary);font-size:13px;font-weight:500;cursor:pointer;margin:1px 0;
  border:1px solid transparent;transition:all 0.15s;}
.sb-item:hover{background:rgba(255,255,255,0.04);color:var(--text-secondary);}
.sb-item.active{background:var(--accent-soft);color:var(--text-primary);border-color:rgba(93,162,255,0.15);}
.sb-item svg{width:15px;height:15px;flex-shrink:0;}
.sb-item.active svg{stroke:var(--accent);}
.sb-item svg{stroke:currentColor;fill:none;stroke-width:1.8;}
.sb-footer{padding:12px;border-top:1px solid var(--border);}
.sb-user{display:flex;align-items:center;gap:10px;padding:10px;border-radius:12px;
  background:rgba(255,255,255,0.03);border:1px solid var(--border);}
.sb-avatar{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#1a3a6b,#2d5a9e);
  display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:#7ab1ff;flex-shrink:0;}
.sb-user-info{flex:1;min-width:0;}
.sb-user-name{font-size:12px;font-weight:600;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.sb-user-role{font-size:10px;color:var(--success);font-family:'IBM Plex Mono',monospace;}
/* Main content */
.main{flex:1;display:flex;flex-direction:column;min-width:0;background:var(--bg-base);}
.top-bar{display:flex;align-items:center;justify-content:space-between;
  padding:0 28px;height:60px;border-bottom:1px solid var(--border);flex-shrink:0;
  background:rgba(5,6,8,0.8);}
.top-bar-title{font-size:15px;font-weight:700;color:var(--text-primary);}
.top-bar-sub{font-size:11px;color:var(--text-muted);margin-left:8px;}
.top-bar-actions{display:flex;gap:8px;align-items:center;}
.content{flex:1;padding:24px 28px;overflow-y:auto;}
/* Cards */
.card{background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);margin-bottom:16px;}
.card-header{display:flex;align-items:center;justify-content:space-between;
  padding:14px 18px;border-bottom:1px solid var(--border);}
.card-title{font-size:12px;font-weight:700;color:var(--text-secondary);letter-spacing:0.04em;text-transform:uppercase;}
.card-body{padding:16px 18px;}
/* Stat tiles */
.stat-grid{display:grid;gap:12px;margin-bottom:20px;}
.stat-grid-4{grid-template-columns:repeat(4,1fr);}
.stat-grid-3{grid-template-columns:repeat(3,1fr);}
.stat-tile{background:var(--bg-surface-2);border:1px solid rgba(255,255,255,0.08);
  border-radius:16px;padding:16px 18px;}
.stat-label{font-size:10px;font-family:'IBM Plex Mono',monospace;text-transform:uppercase;
  letter-spacing:0.12em;color:var(--text-muted);margin-bottom:8px;}
.stat-value{font-size:24px;font-weight:800;color:var(--text-primary);}
.stat-value.accent{color:var(--accent);}
.stat-value.success{color:var(--success);}
.stat-value.warning{color:var(--warning);}
.stat-sub{font-size:11px;color:var(--text-muted);margin-top:4px;}
/* Buttons */
.btn-primary{display:inline-flex;align-items:center;gap:6px;padding:9px 18px;border-radius:999px;
  background:linear-gradient(180deg,#6cb0ff 0%,#4f93ff 100%);color:#06111f;
  font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;border:none;cursor:pointer;}
.btn-secondary{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:999px;
  background:rgba(255,255,255,0.05);border:1px solid var(--border);color:var(--text-secondary);
  font-size:12px;font-weight:600;cursor:pointer;}
.btn-ghost{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:10px;
  background:transparent;border:1px solid transparent;color:var(--text-tertiary);font-size:12px;font-weight:500;}
/* Pills / chips */
.chip{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border-radius:999px;
  border:1px solid var(--border);background:rgba(255,255,255,0.04);
  font-size:10px;font-family:'IBM Plex Mono',monospace;color:var(--text-tertiary);letter-spacing:0.1em;text-transform:uppercase;}
.chip.success{border-color:rgba(70,217,164,0.3);background:rgba(70,217,164,0.08);color:var(--success);}
.chip.warning{border-color:rgba(255,189,102,0.3);background:rgba(255,189,102,0.08);color:var(--warning);}
.chip.danger{border-color:rgba(255,107,125,0.3);background:rgba(255,107,125,0.08);color:var(--danger);}
.chip.accent{border-color:rgba(93,162,255,0.3);background:rgba(93,162,255,0.08);color:var(--accent);}
/* Dot status */
.dot{width:7px;height:7px;border-radius:50%;display:inline-block;}
.dot.green{background:#46d9a4;box-shadow:0 0 6px rgba(70,217,164,0.5);}
.dot.yellow{background:#ffbd66;box-shadow:0 0 6px rgba(255,189,102,0.5);}
.dot.red{background:#ff6b7d;box-shadow:0 0 6px rgba(255,107,125,0.5);}
.dot.blue{background:#5da2ff;box-shadow:0 0 6px rgba(93,162,255,0.5);}
/* Table */
.tbl{width:100%;border-collapse:collapse;}
.tbl th{font-size:10px;font-family:'IBM Plex Mono',monospace;text-transform:uppercase;
  letter-spacing:0.1em;color:var(--text-muted);padding:9px 14px;
  border-bottom:1px solid var(--border);text-align:left;}
.tbl td{padding:11px 14px;border-bottom:1px solid var(--border-soft);vertical-align:middle;}
.tbl tr:last-child td{border-bottom:none;}
.tbl tr:hover td{background:rgba(255,255,255,0.02);}
/* Mono text */
.mono{font-family:'IBM Plex Mono',monospace;}
/* Row layout helpers */
.row{display:flex;gap:16px;margin-bottom:16px;}
.col-half{flex:1;}
/* Input */
.inp{background:rgba(255,255,255,0.04);border:1px solid var(--border);
  border-radius:var(--radius-sm);padding:10px 14px;color:var(--text-primary);
  font-size:13px;width:100%;font-family:'Manrope',sans-serif;}
"""


def sidebar(active: str) -> str:
    nav = [
        ("home", "Dashboard", """<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>"""),
        ("chat", "Chat", """<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>"""),
        ("tasks", "Tasks", """<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>"""),
        ("agents", "Agents", """<circle cx="12" cy="8" r="4"/><path d="M6 20v-2a6 6 0 0 1 12 0v2"/>"""),
        ("runtimes", "Runtimes", """<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>"""),
        ("routing", "Routing", """<path d="M4 6h16M4 12h16M4 18h16"/>"""),
        ("providers", "Providers", """<path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>"""),
        ("knowledge", "Knowledge", """<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>"""),
        ("schedules", "Schedules", """<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>"""),
        ("logs", "Logs", """<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>"""),
        ("settings", "Settings", """<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>"""),
    ]
    items = ""
    for key, label, path in nav:
        cls = "sb-item active" if key == active else "sb-item"
        items += f'<div class="{cls}"><svg viewBox="0 0 24 24"><{path}</svg>{label}</div>\n'
    return f"""
<div class="sidebar">
  <div class="sb-logo">
    <div class="sb-logo-icon">
      <svg viewBox="0 0 24 24"><rect x="4" y="4" width="6" height="6"/><rect x="14" y="4" width="6" height="6"/><rect x="14" y="14" width="6" height="6"/><rect x="4" y="14" width="6" height="6"/></svg>
    </div>
    <div class="sb-logo-text">
      <div class="sb-logo-name">LLM Relay</div>
      <div class="sb-logo-ver">v4.0 · native black</div>
    </div>
  </div>
  <div class="sb-nav">
    <div class="sb-section">Workspace</div>
    {items}
  </div>
  <div class="sb-footer">
    <div class="sb-user">
      <div class="sb-avatar">A</div>
      <div class="sb-user-info">
        <div class="sb-user-name">admin@llmrelay.local</div>
        <div class="sb-user-role">admin</div>
      </div>
    </div>
  </div>
</div>"""


def page(active: str, title: str, subtitle: str, body: str, actions: str = "") -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>{BASE_CSS}</style></head><body>
<div class="layout">
  {sidebar(active)}
  <div class="main">
    <div class="top-bar">
      <div style="display:flex;align-items:baseline;gap:8px;">
        <span class="top-bar-title">{title}</span>
        <span class="top-bar-sub">{subtitle}</span>
      </div>
      <div class="top-bar-actions">{actions}</div>
    </div>
    <div class="content">{body}</div>
  </div>
</div>
</body></html>"""


def shot(name: str, html: str, width: int = 1440, height: int = 900) -> None:
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        f.write(html)
        tmp = f.name
    out = str(OUT.resolve() / name)
    pw = "/opt/node22/bin/playwright"
    result = subprocess.run([
        pw, "screenshot", "--browser", "chromium",
        "--viewport-size", f"{width},{height}",
        "--full-page",
        f"file://{tmp}", out,
    ], capture_output=True, text=True)
    os.unlink(tmp)
    if result.returncode != 0:
        print(f"✗ {name}: {result.stderr.strip()}")
        raise SystemExit(1)
    print(f"✓ {name}")


# ── 1. CONTROL PLANE / DASHBOARD ─────────────────────────────────────────────

DASHBOARD_BODY = """
<div class="stat-grid stat-grid-4">
  <div class="stat-tile">
    <div class="stat-label">Requests today</div>
    <div class="stat-value accent">1,284</div>
    <div class="stat-sub">↑ 12% vs yesterday</div>
  </div>
  <div class="stat-tile">
    <div class="stat-label">Tokens processed</div>
    <div class="stat-value">4.2M</div>
    <div class="stat-sub">In + out combined</div>
  </div>
  <div class="stat-tile">
    <div class="stat-label">Estimated savings</div>
    <div class="stat-value success">$38.40</div>
    <div class="stat-sub">vs cloud API pricing</div>
  </div>
  <div class="stat-tile">
    <div class="stat-label">Active tasks</div>
    <div class="stat-value warning">3</div>
    <div class="stat-sub">2 running · 1 queued</div>
  </div>
</div>

<div class="row">
  <div class="col-half">
    <div class="card">
      <div class="card-header">
        <span class="card-title">Provider Status</span>
        <span class="chip success"><span class="dot green"></span>All healthy</span>
      </div>
      <div class="card-body">
        <div style="display:flex;flex-direction:column;gap:10px;">
          <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 14px;background:var(--bg-surface-2);border:1px solid var(--border);border-radius:14px;">
            <div style="display:flex;align-items:center;gap:10px;">
              <span class="dot green"></span>
              <div>
                <div style="font-size:13px;font-weight:600;color:var(--text-primary);">NVIDIA NIM</div>
                <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">qwen/qwen2.5-coder-32b · priority −10</div>
              </div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:12px;color:var(--success);">340ms avg</div>
              <span class="chip accent" style="font-size:9px;padding:2px 7px;">FREE TIER</span>
            </div>
          </div>
          <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 14px;background:var(--bg-surface-2);border:1px solid var(--border);border-radius:14px;">
            <div style="display:flex;align-items:center;gap:10px;">
              <span class="dot green"></span>
              <div>
                <div style="font-size:13px;font-weight:600;color:var(--text-primary);">Ollama (local)</div>
                <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">qwen3-coder:30b · priority 0</div>
              </div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:12px;color:var(--success);">1.2s avg</div>
              <span class="chip" style="font-size:9px;padding:2px 7px;">LOCAL</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header">
        <span class="card-title">Routing Policy</span>
        <span class="chip accent">free-first</span>
      </div>
      <div class="card-body">
        <div style="display:flex;flex-direction:column;gap:8px;font-size:13px;">
          <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Strategy</span><span style="color:var(--text-primary);font-weight:600;">free-first → local → cloud</span></div>
          <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Timeout per provider</span><span style="color:var(--text-primary);font-weight:600;">30s</span></div>
          <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Cooldown on failure</span><span style="color:var(--text-primary);font-weight:600;">15s · 300s (auth)</span></div>
          <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Classification</span><span style="color:var(--text-primary);font-weight:600;">Auto (complexity)</span></div>
        </div>
      </div>
    </div>
  </div>
  <div class="col-half">
    <div class="card">
      <div class="card-header">
        <span class="card-title">Running Tasks</span>
        <button class="btn-secondary" style="font-size:11px;padding:6px 12px;">View board</button>
      </div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:10px;">
        <div style="padding:12px 14px;background:rgba(93,162,255,0.06);border:1px solid rgba(93,162,255,0.18);border-radius:14px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
            <span style="font-size:13px;font-weight:600;color:var(--text-primary);">Refactor auth middleware</span>
            <span class="chip accent" style="font-size:9px;">running</span>
          </div>
          <div style="font-size:11px;color:var(--text-muted);">Agent: coder-1 · 00:03:12 elapsed · step 4/8</div>
          <div style="margin-top:8px;height:4px;background:rgba(255,255,255,0.08);border-radius:2px;">
            <div style="width:50%;height:4px;background:var(--accent);border-radius:2px;"></div>
          </div>
        </div>
        <div style="padding:12px 14px;background:rgba(93,162,255,0.06);border:1px solid rgba(93,162,255,0.18);border-radius:14px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
            <span style="font-size:13px;font-weight:600;color:var(--text-primary);">Write unit tests for router</span>
            <span class="chip accent" style="font-size:9px;">running</span>
          </div>
          <div style="font-size:11px;color:var(--text-muted);">Agent: coder-2 · 00:01:44 elapsed · step 2/6</div>
          <div style="margin-top:8px;height:4px;background:rgba(255,255,255,0.08);border-radius:2px;">
            <div style="width:33%;height:4px;background:var(--accent);border-radius:2px;"></div>
          </div>
        </div>
        <div style="padding:12px 14px;background:rgba(255,189,102,0.06);border:1px solid rgba(255,189,102,0.2);border-radius:14px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
            <span style="font-size:13px;font-weight:600;color:var(--text-primary);">Summarise PR #84 diff</span>
            <span class="chip warning" style="font-size:9px;">queued</span>
          </div>
          <div style="font-size:11px;color:var(--text-muted);">Waiting for agent slot · deepseek-r1:32b</div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Quick Actions</span></div>
      <div class="card-body" style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
        <div style="padding:14px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);border-radius:14px;cursor:pointer;">
          <div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:3px;">New task</div>
          <div style="font-size:11px;color:var(--text-muted);">Create & run agent job</div>
        </div>
        <div style="padding:14px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);border-radius:14px;cursor:pointer;">
          <div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:3px;">Open chat</div>
          <div style="font-size:11px;color:var(--text-muted);">Direct LLM or agent</div>
        </div>
        <div style="padding:14px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);border-radius:14px;cursor:pointer;">
          <div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:3px;">Add provider</div>
          <div style="font-size:11px;color:var(--text-muted);">Connect new LLM source</div>
        </div>
        <div style="padding:14px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);border-radius:14px;cursor:pointer;">
          <div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:3px;">View logs</div>
          <div style="font-size:11px;color:var(--text-muted);">Activity & trace feed</div>
        </div>
      </div>
    </div>
  </div>
</div>"""

# ── 2. CHAT ───────────────────────────────────────────────────────────────────

CHAT_CSS = """
.chat-wrap{display:flex;flex-direction:column;height:calc(100vh - 60px);}
.chat-header{display:flex;align-items:center;justify-content:space-between;
  padding:12px 20px;border-bottom:1px solid var(--border);background:rgba(5,6,8,0.6);}
.chat-messages{flex:1;overflow-y:auto;padding:24px 20px;display:flex;flex-direction:column;gap:16px;}
.msg-row{display:flex;gap:12px;align-items:flex-start;}
.msg-row.user{flex-direction:row-reverse;}
.msg-avatar{width:30px;height:30px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;}
.msg-avatar.bot{background:#002fa7;color:#7ab1ff;border:1px solid rgba(93,162,255,0.2);}
.msg-avatar.user{background:linear-gradient(135deg,#1a3a6b,#2d5a9e);color:#7ab1ff;}
.msg-bubble{max-width:72%;padding:12px 16px;border-radius:18px;font-size:13px;line-height:1.6;}
.msg-bubble.bot{background:var(--bg-elevated);border:1px solid var(--border);color:var(--text-secondary);border-top-left-radius:6px;}
.msg-bubble.user{background:linear-gradient(135deg,rgba(93,162,255,0.15),rgba(93,162,255,0.08));border:1px solid rgba(93,162,255,0.2);color:var(--text-primary);border-top-right-radius:6px;}
.msg-bubble code{background:rgba(0,0,0,0.3);padding:2px 6px;border-radius:5px;font-family:'IBM Plex Mono',monospace;font-size:11px;color:#86efac;}
.msg-time{font-size:10px;color:var(--text-muted);margin-top:4px;font-family:'IBM Plex Mono',monospace;}
.chat-composer{padding:14px 20px;border-top:1px solid var(--border);background:rgba(5,6,8,0.8);}
.composer-inner{display:flex;align-items:center;gap:10px;background:var(--bg-surface);border:1px solid var(--border);border-radius:999px;padding:8px 16px;}
.composer-inner input{flex:1;background:transparent;border:none;color:var(--text-primary);font-size:13px;outline:none;}
.agent-toggle{display:flex;align-items:center;gap:6px;padding:6px 12px;border-radius:999px;
  background:rgba(255,255,255,0.04);border:1px solid var(--border);font-size:11px;color:var(--text-muted);cursor:pointer;}
.agent-toggle .toggle-dot{width:24px;height:14px;border-radius:7px;background:rgba(255,255,255,0.1);
  position:relative;flex-shrink:0;}
.agent-toggle .toggle-dot.on{background:var(--accent);}
"""

CHAT_BODY = """
<style>""" + CHAT_CSS + """</style>
<div class="chat-wrap">
  <div class="chat-header">
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-size:14px;font-weight:700;color:var(--text-primary);">Direct Chat</span>
      <span class="chip" style="font-size:10px;">qwen/qwen2.5-coder-32b · NIM</span>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
      <div class="agent-toggle">
        <div class="toggle-dot"></div>
        <span>Agent mode</span>
      </div>
      <button class="btn-ghost" style="font-size:11px;">New chat</button>
    </div>
  </div>
  <div class="chat-messages">
    <div class="msg-row user">
      <div class="msg-avatar user">A</div>
      <div>
        <div class="msg-bubble user">Can you write a Python function that validates an API key format and returns a structured result?</div>
        <div class="msg-time" style="text-align:right;">14:23</div>
      </div>
    </div>
    <div class="msg-row">
      <div class="msg-avatar bot">R</div>
      <div>
        <div class="msg-bubble bot">Sure! Here's a clean validation function with a structured result:<br><br>
<code>from dataclasses import dataclass</code><br>
<code>import re</code><br><br>
<code>@dataclass</code><br>
<code>class KeyValidation:</code><br>
<code>&nbsp;&nbsp;&nbsp;&nbsp;valid: bool</code><br>
<code>&nbsp;&nbsp;&nbsp;&nbsp;prefix: str | None</code><br>
<code>&nbsp;&nbsp;&nbsp;&nbsp;error: str | None = None</code><br><br>
This uses a dataclass so you get type-safe access to each field. The regex checks for your <code>sk-relay-</code> prefix followed by alphanumerics.</div>
        <div class="msg-time">14:23</div>
      </div>
    </div>
    <div class="msg-row user">
      <div class="msg-avatar user">A</div>
      <div>
        <div class="msg-bubble user">Add timing info and hash the key before logging it.</div>
        <div class="msg-time" style="text-align:right;">14:24</div>
      </div>
    </div>
    <div class="msg-row">
      <div class="msg-avatar bot">R</div>
      <div>
        <div class="msg-bubble bot">Updated version with timing via <code>time.perf_counter()</code> and SHA-256 hashing so you never log the raw key value. The <code>KeyValidation</code> dataclass gains a <code>duration_ms</code> field and the logger always receives the hashed form.</div>
        <div class="msg-time">14:24</div>
      </div>
    </div>
  </div>
  <div class="chat-composer">
    <div style="margin-bottom:10px;display:flex;gap:8px;">
      <span class="chip" style="cursor:pointer;">Explain code</span>
      <span class="chip" style="cursor:pointer;">Write tests</span>
      <span class="chip" style="cursor:pointer;">Refactor</span>
      <span class="chip" style="cursor:pointer;">Review PR</span>
    </div>
    <div class="composer-inner">
      <input placeholder="Ask anything — or enable Agent mode for multi-step tasks…" />
      <button class="btn-primary" style="padding:8px 20px;font-size:11px;">Send</button>
    </div>
  </div>
</div>"""

# ── 3. TASK BOARD ─────────────────────────────────────────────────────────────

TASKS_CSS = """
.kanban{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;align-items:start;}
.k-col{background:var(--bg-surface-2);border:1px solid var(--border);border-radius:var(--radius);padding:14px;}
.k-col-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;}
.k-col-title{font-size:11px;font-weight:700;color:var(--text-muted);letter-spacing:0.1em;text-transform:uppercase;font-family:'IBM Plex Mono',monospace;}
.k-count{background:rgba(255,255,255,0.08);border-radius:99px;padding:2px 8px;font-size:11px;color:var(--text-muted);}
.k-card{background:var(--bg-elevated);border:1px solid var(--border);border-radius:16px;padding:14px;margin-bottom:10px;}
.k-card:last-child{margin-bottom:0;}
.k-card-title{font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:6px;line-height:1.4;}
.k-card-meta{font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;}
.k-card-tags{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px;}
.k-progress{margin-top:10px;height:3px;background:rgba(255,255,255,0.08);border-radius:2px;}
.k-progress-fill{height:3px;border-radius:2px;background:var(--accent);}
"""

TASKS_BODY = f"""<style>{TASKS_CSS}</style>
<div class="kanban">
  <div class="k-col">
    <div class="k-col-header">
      <span class="k-col-title">Queued</span>
      <span class="k-count">2</span>
    </div>
    <div class="k-card">
      <div class="k-card-title">Summarise PR #84 diff and post comment</div>
      <div class="k-card-meta">deepseek-r1:32b · coder-2</div>
      <div class="k-card-tags">
        <span class="chip" style="font-size:9px;padding:2px 7px;">github</span>
        <span class="chip warning" style="font-size:9px;padding:2px 7px;">queued</span>
      </div>
    </div>
    <div class="k-card">
      <div class="k-card-title">Update API docs for v4 async job endpoints</div>
      <div class="k-card-meta">qwen2.5-coder-32b · coder-1</div>
      <div class="k-card-tags">
        <span class="chip" style="font-size:9px;padding:2px 7px;">docs</span>
        <span class="chip warning" style="font-size:9px;padding:2px 7px;">queued</span>
      </div>
    </div>
  </div>
  <div class="k-col">
    <div class="k-col-header">
      <span class="k-col-title">Running</span>
      <span class="k-count" style="background:rgba(93,162,255,0.15);color:var(--accent);">2</span>
    </div>
    <div class="k-card" style="border-color:rgba(93,162,255,0.2);background:rgba(93,162,255,0.04);">
      <div class="k-card-title">Refactor auth middleware to async context managers</div>
      <div class="k-card-meta">qwen2.5-coder-32b · coder-1 · 3m 12s</div>
      <div class="k-card-tags">
        <span class="chip accent" style="font-size:9px;padding:2px 7px;">running</span>
        <span class="chip" style="font-size:9px;padding:2px 7px;">step 4/8</span>
      </div>
      <div class="k-progress"><div class="k-progress-fill" style="width:50%;"></div></div>
    </div>
    <div class="k-card" style="border-color:rgba(93,162,255,0.2);background:rgba(93,162,255,0.04);">
      <div class="k-card-title">Write unit tests for ModelRouter classifier</div>
      <div class="k-card-meta">qwen2.5-coder-32b · coder-2 · 1m 44s</div>
      <div class="k-card-tags">
        <span class="chip accent" style="font-size:9px;padding:2px 7px;">running</span>
        <span class="chip" style="font-size:9px;padding:2px 7px;">step 2/6</span>
      </div>
      <div class="k-progress"><div class="k-progress-fill" style="width:33%;"></div></div>
    </div>
  </div>
  <div class="k-col">
    <div class="k-col-header">
      <span class="k-col-title">In Review</span>
      <span class="k-count">1</span>
    </div>
    <div class="k-card" style="border-color:rgba(255,189,102,0.2);background:rgba(255,189,102,0.03);">
      <div class="k-card-title">Add NVIDIA NIM provider card to setup wizard</div>
      <div class="k-card-meta">qwen2.5-coder-32b · judge gate pending</div>
      <div class="k-card-tags">
        <span class="chip warning" style="font-size:9px;padding:2px 7px;">in review</span>
        <span class="chip" style="font-size:9px;padding:2px 7px;">frontend</span>
      </div>
    </div>
  </div>
  <div class="k-col">
    <div class="k-col-header">
      <span class="k-col-title">Done</span>
      <span class="k-count" style="background:rgba(70,217,164,0.12);color:var(--success);">5</span>
    </div>
    <div class="k-card">
      <div class="k-card-title">Fix async job polling 401 in hosted chat</div>
      <div class="k-card-meta">3 files · APPROVED</div>
      <div class="k-card-tags">
        <span class="chip success" style="font-size:9px;padding:2px 7px;">done</span>
      </div>
    </div>
    <div class="k-card">
      <div class="k-card-title">Bounded provider timeouts + cooldown tiers</div>
      <div class="k-card-meta">2 files · APPROVED</div>
      <div class="k-card-tags">
        <span class="chip success" style="font-size:9px;padding:2px 7px;">done</span>
      </div>
    </div>
    <div class="k-card">
      <div class="k-card-title">Mobile dark app shell — login + setup</div>
      <div class="k-card-meta">4 files · APPROVED</div>
      <div class="k-card-tags">
        <span class="chip success" style="font-size:9px;padding:2px 7px;">done</span>
      </div>
    </div>
  </div>
</div>"""

# ── 4. AGENTS ─────────────────────────────────────────────────────────────────

AGENTS_BODY = """
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;">

  <div class="card">
    <div class="card-header">
      <div>
        <div style="font-size:14px;font-weight:700;color:var(--text-primary);">coder-1</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:2px;font-family:'IBM Plex Mono',monospace;">internal-agent runtime</div>
      </div>
      <span class="chip success"><span class="dot green"></span>idle</span>
    </div>
    <div class="card-body" style="display:flex;flex-direction:column;gap:8px;font-size:12px;">
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Role</span><span style="color:var(--text-primary);font-weight:600;">executor / coder</span></div>
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Planner model</span><span style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;">nemotron-super-120b</span></div>
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Coder model</span><span style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;">qwen2.5-coder-32b</span></div>
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Verifier model</span><span style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;">nemotron-super-120b</span></div>
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Judge model</span><span style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;">nemotron-super-120b</span></div>
      <div style="border-top:1px solid var(--border);padding-top:8px;display:flex;gap:5px;flex-wrap:wrap;">
        <span class="chip" style="font-size:9px;padding:2px 7px;">refactor</span>
        <span class="chip" style="font-size:9px;padding:2px 7px;">tests</span>
        <span class="chip" style="font-size:9px;padding:2px 7px;">bugfix</span>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <div>
        <div style="font-size:14px;font-weight:700;color:var(--text-primary);">coder-2</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:2px;font-family:'IBM Plex Mono',monospace;">internal-agent runtime</div>
      </div>
      <span class="chip accent"><span class="dot blue"></span>running</span>
    </div>
    <div class="card-body" style="display:flex;flex-direction:column;gap:8px;font-size:12px;">
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Role</span><span style="color:var(--text-primary);font-weight:600;">executor / coder</span></div>
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Planner model</span><span style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;">nemotron-super-120b</span></div>
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Coder model</span><span style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;">qwen2.5-coder-32b</span></div>
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Verifier model</span><span style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;">nemotron-super-120b</span></div>
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Judge model</span><span style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;">nemotron-super-120b</span></div>
      <div style="border-top:1px solid var(--border);padding-top:8px;display:flex;gap:5px;">
        <span class="chip" style="font-size:9px;padding:2px 7px;">tests</span>
        <span class="chip" style="font-size:9px;padding:2px 7px;">docs</span>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <div>
        <div style="font-size:14px;font-weight:700;color:var(--text-primary);">researcher</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:2px;font-family:'IBM Plex Mono',monospace;">internal-agent runtime</div>
      </div>
      <span class="chip success"><span class="dot green"></span>idle</span>
    </div>
    <div class="card-body" style="display:flex;flex-direction:column;gap:8px;font-size:12px;">
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Role</span><span style="color:var(--text-primary);font-weight:600;">researcher / analyst</span></div>
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Planner model</span><span style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;">deepseek-r1:32b</span></div>
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Executor model</span><span style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;">deepseek-r1:32b</span></div>
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Verifier model</span><span style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;">deepseek-r1:32b</span></div>
      <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Tasks completed</span><span style="color:var(--text-primary);font-weight:600;">47</span></div>
      <div style="border-top:1px solid var(--border);padding-top:8px;display:flex;gap:5px;">
        <span class="chip" style="font-size:9px;padding:2px 7px;">research</span>
        <span class="chip" style="font-size:9px;padding:2px 7px;">analysis</span>
        <span class="chip" style="font-size:9px;padding:2px 7px;">summarise</span>
      </div>
    </div>
  </div>

</div>
<div style="margin-top:14px;display:flex;gap:10px;">
  <button class="btn-primary">+ New agent</button>
  <button class="btn-secondary">Configure defaults</button>
</div>"""

# ── 5. RUNTIMES ───────────────────────────────────────────────────────────────

RUNTIMES_BODY = """
<div style="display:flex;flex-direction:column;gap:14px;">

  <div class="card">
    <div class="card-header">
      <div style="display:flex;align-items:center;gap:10px;">
        <span class="dot green"></span>
        <div>
          <div style="font-size:14px;font-weight:700;color:var(--text-primary);">internal-agent</div>
          <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">Built-in Python agent loop · always available</div>
        </div>
      </div>
      <span class="chip success">preflight OK</span>
    </div>
    <div class="card-body">
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;font-size:12px;">
        <div><span style="color:var(--text-muted);">Max steps</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">20</div></div>
        <div><span style="color:var(--text-muted);">Timeout</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">120s</div></div>
        <div><span style="color:var(--text-muted);">Tools</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">read, write, bash, search</div></div>
        <div><span style="color:var(--text-muted);">Subagents</span><div style="font-weight:600;color:var(--success);margin-top:3px;">✓ enabled</div></div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <div style="display:flex;align-items:center;gap:10px;">
        <span class="dot yellow"></span>
        <div>
          <div style="font-size:14px;font-weight:700;color:var(--text-primary);">docker-sandbox</div>
          <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">Isolated Docker container execution</div>
        </div>
      </div>
      <span class="chip warning">Docker socket unavailable</span>
    </div>
    <div class="card-body">
      <div style="background:rgba(255,189,102,0.06);border:1px solid rgba(255,189,102,0.2);border-radius:12px;padding:12px;font-size:12px;color:var(--warning);">
        Preflight check: <code style="font-family:'IBM Plex Mono',monospace;">/var/run/docker.sock</code> not found. Start the Docker daemon or set <code style="font-family:'IBM Plex Mono',monospace;">DOCKER_HOST</code> to use this runtime.
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <div style="display:flex;align-items:center;gap:10px;">
        <span class="dot green"></span>
        <div>
          <div style="font-size:14px;font-weight:700;color:var(--text-primary);">task-harness</div>
          <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">External task-harness binary · configurable</div>
        </div>
      </div>
      <span class="chip success">preflight OK</span>
    </div>
    <div class="card-body">
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;font-size:12px;">
        <div><span style="color:var(--text-muted);">Binary</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;font-family:'IBM Plex Mono',monospace;">task-harness</div></div>
        <div><span style="color:var(--text-muted);">Version</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">2.1.0</div></div>
        <div><span style="color:var(--text-muted);">Approval gate</span><div style="font-weight:600;color:var(--success);margin-top:3px;">✓ enabled</div></div>
      </div>
    </div>
  </div>

</div>"""

# ── 6. ROUTING ────────────────────────────────────────────────────────────────

ROUTING_BODY = """
<div class="row">
  <div class="col-half">
    <div class="card">
      <div class="card-header"><span class="card-title">Active Policy</span><span class="chip accent">free-first</span></div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:12px;">
        <div>
          <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Strategy</div>
          <div style="display:flex;gap:8px;">
            <div style="padding:9px 14px;border-radius:10px;background:var(--accent-soft);border:1px solid rgba(93,162,255,0.2);font-size:12px;font-weight:600;color:var(--accent);">free-first</div>
            <div style="padding:9px 14px;border-radius:10px;background:rgba(255,255,255,0.03);border:1px solid var(--border);font-size:12px;color:var(--text-muted);">local-first</div>
            <div style="padding:9px 14px;border-radius:10px;background:rgba(255,255,255,0.03);border:1px solid var(--border);font-size:12px;color:var(--text-muted);">cost-aware</div>
            <div style="padding:9px 14px;border-radius:10px;background:rgba(255,255,255,0.03);border:1px solid var(--border);font-size:12px;color:var(--text-muted);">quality</div>
          </div>
        </div>
        <div style="font-size:12px;color:var(--text-muted);line-height:1.6;padding:10px;background:rgba(255,255,255,0.02);border-radius:10px;border:1px solid var(--border-soft);">
          Tries NVIDIA NIM free-tier first (priority −10), then local Ollama models, then paid cloud providers. Bounded 30s timeout per provider. Failure-type-aware cooldowns: 15s on connection error, 300s on auth failure.
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Complexity Classifier</span></div>
      <div class="card-body" style="font-size:12px;display:flex;flex-direction:column;gap:8px;">
        <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Simple threshold</span><span style="color:var(--text-primary);font-weight:600;">≤ 3 words → direct LLM</span></div>
        <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Complex trigger</span><span style="color:var(--text-primary);font-weight:600;">code/agent keywords</span></div>
        <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Agent mode override</span><span style="color:var(--text-primary);font-weight:600;">user toggle</span></div>
        <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Agent timeout</span><span style="color:var(--text-primary);font-weight:600;">120s (8 max steps)</span></div>
      </div>
    </div>
  </div>
  <div class="col-half">
    <div class="card">
      <div class="card-header"><span class="card-title">Provider Priority Order</span></div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:8px;">
        <div style="display:flex;align-items:center;gap:12px;padding:12px;background:rgba(93,162,255,0.05);border:1px solid rgba(93,162,255,0.15);border-radius:12px;">
          <div style="width:28px;height:28px;border-radius:8px;background:rgba(93,162,255,0.12);border:1px solid rgba(93,162,255,0.2);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--accent);">1</div>
          <div style="flex:1;">
            <div style="font-size:13px;font-weight:600;color:var(--text-primary);">NVIDIA NIM</div>
            <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">priority −10 · free tier · auto-configured</div>
          </div>
          <span class="dot green"></span>
        </div>
        <div style="display:flex;align-items:center;gap:12px;padding:12px;background:rgba(255,255,255,0.02);border:1px solid var(--border);border-radius:12px;">
          <div style="width:28px;height:28px;border-radius:8px;background:rgba(255,255,255,0.05);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--text-muted);">2</div>
          <div style="flex:1;">
            <div style="font-size:13px;font-weight:600;color:var(--text-primary);">Ollama (local)</div>
            <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">priority 0 · qwen3-coder:30b</div>
          </div>
          <span class="dot green"></span>
        </div>
        <div style="display:flex;align-items:center;gap:12px;padding:12px;background:rgba(255,255,255,0.02);border:1px solid var(--border);border-radius:12px;">
          <div style="width:28px;height:28px;border-radius:8px;background:rgba(255,255,255,0.05);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--text-muted);">3</div>
          <div style="flex:1;">
            <div style="font-size:13px;font-weight:600;color:var(--text-primary);">Anthropic (cloud)</div>
            <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">priority 10 · fallback only</div>
          </div>
          <span class="dot green"></span>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Routing Stats (24h)</span></div>
      <div class="card-body">
        <div class="stat-grid stat-grid-3">
          <div class="stat-tile"><div class="stat-label">NIM hits</div><div class="stat-value accent" style="font-size:20px;">841</div><div class="stat-sub">66%</div></div>
          <div class="stat-tile"><div class="stat-label">Local hits</div><div class="stat-value" style="font-size:20px;">381</div><div class="stat-sub">30%</div></div>
          <div class="stat-tile"><div class="stat-label">Fallbacks</div><div class="stat-value warning" style="font-size:20px;">62</div><div class="stat-sub">4%</div></div>
        </div>
      </div>
    </div>
  </div>
</div>"""

# ── 7. PROVIDERS ──────────────────────────────────────────────────────────────

PROVIDERS_BODY = """
<div style="margin-bottom:14px;display:flex;justify-content:flex-end;">
  <button class="btn-primary">+ Add provider</button>
</div>
<div style="display:flex;flex-direction:column;gap:12px;">

  <div class="card" style="border-color:rgba(93,162,255,0.2);background:rgba(93,162,255,0.03);">
    <div class="card-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="width:38px;height:38px;border-radius:10px;background:rgba(93,162,255,0.12);border:1px solid rgba(93,162,255,0.2);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;color:var(--accent);">N</div>
        <div>
          <div style="font-size:14px;font-weight:700;color:var(--text-primary);">NVIDIA NIM</div>
          <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">integrate.api.nvidia.com/v1 · priority −10</div>
        </div>
        <span class="chip accent" style="font-size:9px;padding:2px 8px;">★ RECOMMENDED</span>
        <span class="chip success" style="font-size:9px;padding:2px 8px;">FREE TIER</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="dot green"></span>
        <span style="font-size:12px;color:var(--success);">healthy · 340ms</span>
      </div>
    </div>
    <div class="card-body" style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;font-size:12px;">
      <div><span style="color:var(--text-muted);">Default model</span><div style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;margin-top:3px;">qwen2.5-coder-32b</div></div>
      <div><span style="color:var(--text-muted);">Models available</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">12</div></div>
      <div><span style="color:var(--text-muted);">Requests (24h)</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">841</div></div>
      <div><span style="color:var(--text-muted);">Auth</span><div style="color:var(--success);margin-top:3px;">NVIDIA_API_KEY ✓</div></div>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="width:38px;height:38px;border-radius:10px;background:rgba(255,255,255,0.05);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;color:var(--text-secondary);">O</div>
        <div>
          <div style="font-size:14px;font-weight:700;color:var(--text-primary);">Ollama (local)</div>
          <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">localhost:11434 · priority 0</div>
        </div>
        <span class="chip" style="font-size:9px;padding:2px 8px;">LOCAL</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="dot green"></span>
        <span style="font-size:12px;color:var(--success);">healthy · 1.2s</span>
      </div>
    </div>
    <div class="card-body" style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;font-size:12px;">
      <div><span style="color:var(--text-muted);">Default model</span><div style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;margin-top:3px;">qwen3-coder:30b</div></div>
      <div><span style="color:var(--text-muted);">Models loaded</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">3</div></div>
      <div><span style="color:var(--text-muted);">Requests (24h)</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">381</div></div>
      <div><span style="color:var(--text-muted);">Auth</span><div style="color:var(--success);margin-top:3px;">None (local)</div></div>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="width:38px;height:38px;border-radius:10px;background:rgba(255,255,255,0.05);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;color:var(--text-secondary);">A</div>
        <div>
          <div style="font-size:14px;font-weight:700;color:var(--text-primary);">Anthropic</div>
          <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">api.anthropic.com · priority 10 · fallback</div>
        </div>
        <span class="chip" style="font-size:9px;padding:2px 8px;">CLOUD</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="dot green"></span>
        <span style="font-size:12px;color:var(--success);">healthy · 820ms</span>
      </div>
    </div>
    <div class="card-body" style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;font-size:12px;">
      <div><span style="color:var(--text-muted);">Default model</span><div style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:11px;margin-top:3px;">claude-sonnet-4-6</div></div>
      <div><span style="color:var(--text-muted);">Requests (24h)</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">62</div></div>
      <div><span style="color:var(--text-muted);">Cost (24h)</span><div style="font-weight:600;color:var(--warning);margin-top:3px;">$1.84</div></div>
      <div><span style="color:var(--text-muted);">Auth</span><div style="color:var(--success);margin-top:3px;">ANTHROPIC_API_KEY ✓</div></div>
    </div>
  </div>

</div>"""


# ── 8. MODELS ─────────────────────────────────────────────────────────────────

MODELS_BODY = """
<table class="tbl">
  <thead>
    <tr>
      <th>Model</th><th>Provider</th><th>Context</th><th>Type</th><th>Cost</th><th>Status</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--text-primary);">qwen/qwen2.5-coder-32b-instruct</span></td>
      <td><span class="chip accent" style="font-size:9px;padding:2px 7px;">NVIDIA NIM</span></td>
      <td style="color:var(--text-muted);font-size:12px;">128k</td>
      <td><span class="chip" style="font-size:9px;padding:2px 7px;">coder</span></td>
      <td style="color:var(--success);font-size:12px;">Free</td>
      <td><span class="dot green"></span></td>
    </tr>
    <tr>
      <td><span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--text-primary);">nvidia/nemotron-super-120b-a12b</span></td>
      <td><span class="chip accent" style="font-size:9px;padding:2px 7px;">NVIDIA NIM</span></td>
      <td style="color:var(--text-muted);font-size:12px;">128k</td>
      <td><span class="chip" style="font-size:9px;padding:2px 7px;">reasoning</span></td>
      <td style="color:var(--success);font-size:12px;">Free</td>
      <td><span class="dot green"></span></td>
    </tr>
    <tr>
      <td><span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--text-primary);">deepseek-ai/deepseek-r1</span></td>
      <td><span class="chip accent" style="font-size:9px;padding:2px 7px;">NVIDIA NIM</span></td>
      <td style="color:var(--text-muted);font-size:12px;">64k</td>
      <td><span class="chip" style="font-size:9px;padding:2px 7px;">reasoning</span></td>
      <td style="color:var(--success);font-size:12px;">Free</td>
      <td><span class="dot green"></span></td>
    </tr>
    <tr>
      <td><span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--text-primary);">qwen3-coder:30b</span></td>
      <td><span class="chip" style="font-size:9px;padding:2px 7px;">Ollama</span></td>
      <td style="color:var(--text-muted);font-size:12px;">32k</td>
      <td><span class="chip" style="font-size:9px;padding:2px 7px;">coder</span></td>
      <td style="color:var(--success);font-size:12px;">Local</td>
      <td><span class="dot green"></span></td>
    </tr>
    <tr>
      <td><span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--text-primary);">deepseek-r1:32b</span></td>
      <td><span class="chip" style="font-size:9px;padding:2px 7px;">Ollama</span></td>
      <td style="color:var(--text-muted);font-size:12px;">32k</td>
      <td><span class="chip" style="font-size:9px;padding:2px 7px;">reasoning</span></td>
      <td style="color:var(--success);font-size:12px;">Local</td>
      <td><span class="dot green"></span></td>
    </tr>
    <tr>
      <td><span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--text-primary);">claude-sonnet-4-6</span></td>
      <td><span class="chip" style="font-size:9px;padding:2px 7px;">Anthropic</span></td>
      <td style="color:var(--text-muted);font-size:12px;">200k</td>
      <td><span class="chip" style="font-size:9px;padding:2px 7px;">general</span></td>
      <td style="color:var(--warning);font-size:12px;">$3/$15 /M</td>
      <td><span class="dot green"></span></td>
    </tr>
    <tr>
      <td><span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--text-primary);">claude-opus-4-7</span></td>
      <td><span class="chip" style="font-size:9px;padding:2px 7px;">Anthropic</span></td>
      <td style="color:var(--text-muted);font-size:12px;">200k</td>
      <td><span class="chip" style="font-size:9px;padding:2px 7px;">general</span></td>
      <td style="color:var(--warning);font-size:12px;">$15/$75 /M</td>
      <td><span class="dot green"></span></td>
    </tr>
  </tbody>
</table>"""

# ── 9. KNOWLEDGE ──────────────────────────────────────────────────────────────

KNOWLEDGE_BODY = """
<div class="row">
  <div style="flex:1.4;">
    <div class="card">
      <div class="card-header">
        <span class="card-title">Wiki Pages</span>
        <button class="btn-primary" style="font-size:11px;padding:7px 14px;">+ New page</button>
      </div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:8px;">
        <input class="inp" placeholder="Search wiki…" style="margin-bottom:4px;" />
        <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 14px;background:var(--bg-surface-2);border:1px solid var(--border);border-radius:12px;cursor:pointer;">
          <div>
            <div style="font-size:13px;font-weight:600;color:var(--text-primary);">Agent pipeline architecture</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">Plan → Execute → Verify → Judge · updated 2 days ago</div>
          </div>
          <span class="chip" style="font-size:9px;padding:2px 7px;">architecture</span>
        </div>
        <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 14px;background:var(--bg-surface-2);border:1px solid var(--border);border-radius:12px;cursor:pointer;">
          <div>
            <div style="font-size:13px;font-weight:600;color:var(--text-primary);">NVIDIA NIM setup guide</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">Free-tier configuration, models, and limits · updated 1 day ago</div>
          </div>
          <span class="chip" style="font-size:9px;padding:2px 7px;">setup</span>
        </div>
        <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 14px;background:var(--bg-surface-2);border:1px solid var(--border);border-radius:12px;cursor:pointer;">
          <div>
            <div style="font-size:13px;font-weight:600;color:var(--text-primary);">Routing policy playbook</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">free-first vs local-first vs cost-aware · updated 3 days ago</div>
          </div>
          <span class="chip" style="font-size:9px;padding:2px 7px;">routing</span>
        </div>
        <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 14px;background:var(--bg-surface-2);border:1px solid var(--border);border-radius:12px;cursor:pointer;">
          <div>
            <div style="font-size:13px;font-weight:600;color:var(--text-primary);">Team onboarding checklist</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">New member setup steps · updated 1 week ago</div>
          </div>
          <span class="chip" style="font-size:9px;padding:2px 7px;">onboarding</span>
        </div>
        <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 14px;background:var(--bg-surface-2);border:1px solid var(--border);border-radius:12px;cursor:pointer;">
          <div>
            <div style="font-size:13px;font-weight:600;color:var(--text-primary);">Langfuse observability notes</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">Traces, token counts, cost attribution · updated 4 days ago</div>
          </div>
          <span class="chip" style="font-size:9px;padding:2px 7px;">observability</span>
        </div>
      </div>
    </div>
  </div>
  <div style="flex:1;">
    <div class="card">
      <div class="card-header">
        <span class="card-title">Sources</span>
        <button class="btn-secondary" style="font-size:11px;padding:7px 14px;">+ Import</button>
      </div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:8px;">
        <div style="padding:12px 14px;background:var(--bg-surface-2);border:1px solid var(--border);border-radius:12px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
            <span style="font-size:13px;font-weight:600;color:var(--text-primary);">strikersam/local-llm-server</span>
            <span class="chip" style="font-size:9px;padding:2px 7px;">github</span>
          </div>
          <div style="font-size:11px;color:var(--text-muted);">233 files indexed · synced 1h ago</div>
        </div>
        <div style="padding:12px 14px;background:var(--bg-surface-2);border:1px solid var(--border);border-radius:12px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
            <span style="font-size:13px;font-weight:600;color:var(--text-primary);">NVIDIA NIM docs</span>
            <span class="chip" style="font-size:9px;padding:2px 7px;">url</span>
          </div>
          <div style="font-size:11px;color:var(--text-muted);">12 pages · synced 6h ago</div>
        </div>
        <div style="padding:12px 14px;background:var(--bg-surface-2);border:1px solid var(--border);border-radius:12px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
            <span style="font-size:13px;font-weight:600;color:var(--text-primary);">Internal API spec (PDF)</span>
            <span class="chip" style="font-size:9px;padding:2px 7px;">file</span>
          </div>
          <div style="font-size:11px;color:var(--text-muted);">48 pages · uploaded 2 days ago</div>
        </div>
      </div>
    </div>
  </div>
</div>"""

# ── 10. LOGS ──────────────────────────────────────────────────────────────────

LOGS_BODY = """
<div class="row" style="margin-bottom:16px;">
  <div class="col-half">
    <div class="stat-grid stat-grid-3">
      <div class="stat-tile"><div class="stat-label">Events (24h)</div><div class="stat-value accent" style="font-size:20px;">1,284</div></div>
      <div class="stat-tile"><div class="stat-label">Warnings</div><div class="stat-value warning" style="font-size:20px;">14</div></div>
      <div class="stat-tile"><div class="stat-label">Errors</div><div class="stat-value danger" style="font-size:20px;">2</div></div>
    </div>
  </div>
  <div style="display:flex;gap:8px;align-items:flex-start;padding-top:4px;">
    <input class="inp" placeholder="Filter logs…" style="width:220px;" />
    <button class="btn-secondary" style="font-size:11px;padding:10px 14px;white-space:nowrap;">All levels</button>
  </div>
</div>
<div class="card">
  <div class="card-body" style="padding:0;font-family:'IBM Plex Mono',monospace;font-size:12px;">
    <div style="display:flex;align-items:flex-start;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border-soft);">
      <span style="color:var(--text-muted);white-space:nowrap;">14:31:02</span>
      <span class="chip success" style="font-size:9px;padding:1px 6px;white-space:nowrap;">INFO</span>
      <span style="color:var(--text-secondary);">chat/send → NIM qwen2.5-coder-32b · 847 tokens · 340ms · saved $0.012
        <span style="color:var(--accent);cursor:pointer;margin-left:6px;">[trace]</span></span>
    </div>
    <div style="display:flex;align-items:flex-start;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border-soft);">
      <span style="color:var(--text-muted);white-space:nowrap;">14:30:58</span>
      <span class="chip success" style="font-size:9px;padding:1px 6px;white-space:nowrap;">INFO</span>
      <span style="color:var(--text-secondary);">agent/job coder-1 · step 4/8 complete · wrote proxy.py (+42 lines)</span>
    </div>
    <div style="display:flex;align-items:flex-start;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border-soft);background:rgba(255,189,102,0.03);">
      <span style="color:var(--text-muted);white-space:nowrap;">14:30:41</span>
      <span class="chip warning" style="font-size:9px;padding:1px 6px;white-space:nowrap;">WARN</span>
      <span style="color:var(--text-secondary);">provider ollama-local · latency spike 4.8s (threshold 3s) · continuing</span>
    </div>
    <div style="display:flex;align-items:flex-start;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border-soft);">
      <span style="color:var(--text-muted);white-space:nowrap;">14:30:22</span>
      <span class="chip success" style="font-size:9px;padding:1px 6px;white-space:nowrap;">INFO</span>
      <span style="color:var(--text-secondary);">chat/send → NIM qwen2.5-coder-32b · 1,204 tokens · 520ms · saved $0.019
        <span style="color:var(--accent);cursor:pointer;margin-left:6px;">[trace]</span></span>
    </div>
    <div style="display:flex;align-items:flex-start;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border-soft);">
      <span style="color:var(--text-muted);white-space:nowrap;">14:29:55</span>
      <span class="chip success" style="font-size:9px;padding:1px 6px;white-space:nowrap;">INFO</span>
      <span style="color:var(--text-secondary);">agent/job coder-2 started · task "Write unit tests for router" · job_id=j_4kx9</span>
    </div>
    <div style="display:flex;align-items:flex-start;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border-soft);background:rgba(255,107,125,0.03);">
      <span style="color:var(--text-muted);white-space:nowrap;">14:28:30</span>
      <span class="chip danger" style="font-size:9px;padding:1px 6px;white-space:nowrap;">ERROR</span>
      <span style="color:var(--text-secondary);">provider anthropic · 429 rate limit · cooldown 30s · falling back to NIM</span>
    </div>
    <div style="display:flex;align-items:flex-start;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border-soft);">
      <span style="color:var(--text-muted);white-space:nowrap;">14:28:11</span>
      <span class="chip success" style="font-size:9px;padding:1px 6px;white-space:nowrap;">INFO</span>
      <span style="color:var(--text-secondary);">schedule "daily-standup" triggered · agent researcher · job_id=j_3mx1</span>
    </div>
    <div style="display:flex;align-items:flex-start;gap:12px;padding:12px 16px;">
      <span style="color:var(--text-muted);white-space:nowrap;">14:27:48</span>
      <span class="chip success" style="font-size:9px;padding:1px 6px;white-space:nowrap;">INFO</span>
      <span style="color:var(--text-secondary);">chat/send → NIM qwen2.5-coder-32b · 312 tokens · 280ms · saved $0.004
        <span style="color:var(--accent);cursor:pointer;margin-left:6px;">[trace]</span></span>
    </div>
  </div>
</div>"""

# ── 11. SCHEDULES ─────────────────────────────────────────────────────────────

SCHEDULES_BODY = """
<div style="margin-bottom:14px;display:flex;justify-content:flex-end;">
  <button class="btn-primary">+ New schedule</button>
</div>
<div style="display:flex;flex-direction:column;gap:12px;">

  <div class="card">
    <div class="card-header">
      <div>
        <div style="font-size:14px;font-weight:700;color:var(--text-primary);">daily-standup</div>
        <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">0 9 * * 1-5 · weekdays 09:00</div>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        <button class="btn-secondary" style="font-size:11px;padding:6px 12px;">Run now</button>
        <span class="chip success"><span class="dot green"></span>active</span>
      </div>
    </div>
    <div class="card-body" style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;font-size:12px;">
      <div><span style="color:var(--text-muted);">Agent</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">researcher</div></div>
      <div><span style="color:var(--text-muted);">Last run</span><div style="font-weight:600;color:var(--success);margin-top:3px;">Today 09:00 ✓</div></div>
      <div><span style="color:var(--text-muted);">Next run</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">Tomorrow 09:00</div></div>
      <div><span style="color:var(--text-muted);">Failures</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">0</div></div>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <div>
        <div style="font-size:14px;font-weight:700;color:var(--text-primary);">weekly-dep-audit</div>
        <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">0 8 * * 1 · Monday 08:00</div>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        <button class="btn-secondary" style="font-size:11px;padding:6px 12px;">Run now</button>
        <span class="chip success"><span class="dot green"></span>active</span>
      </div>
    </div>
    <div class="card-body" style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;font-size:12px;">
      <div><span style="color:var(--text-muted);">Agent</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">coder-1</div></div>
      <div><span style="color:var(--text-muted);">Last run</span><div style="font-weight:600;color:var(--success);margin-top:3px;">Mon 08:00 ✓</div></div>
      <div><span style="color:var(--text-muted);">Next run</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">Mon 08:00</div></div>
      <div><span style="color:var(--text-muted);">Failures</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">0</div></div>
    </div>
  </div>

  <div class="card" style="opacity:0.7;">
    <div class="card-header">
      <div>
        <div style="font-size:14px;font-weight:700;color:var(--text-primary);">nightly-sync</div>
        <div style="font-size:11px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;">0 2 * * * · daily 02:00</div>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        <button class="btn-secondary" style="font-size:11px;padding:6px 12px;">Run now</button>
        <span class="chip"><span class="dot" style="background:var(--text-muted);"></span>paused</span>
      </div>
    </div>
    <div class="card-body" style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;font-size:12px;">
      <div><span style="color:var(--text-muted);">Agent</span><div style="font-weight:600;color:var(--text-primary);margin-top:3px;">researcher</div></div>
      <div><span style="color:var(--text-muted);">Last run</span><div style="font-weight:600;color:var(--text-muted);margin-top:3px;">3 days ago</div></div>
      <div><span style="color:var(--text-muted);">Next run</span><div style="font-weight:600;color:var(--text-muted);margin-top:3px;">Paused</div></div>
      <div><span style="color:var(--text-muted);">Failures</span><div style="font-weight:600;color:var(--warning);margin-top:3px;">1</div></div>
    </div>
  </div>

</div>"""

# ── 12. SETTINGS ──────────────────────────────────────────────────────────────

SETTINGS_BODY = """
<div class="row">
  <div class="col-half">
    <div class="card">
      <div class="card-header"><span class="card-title">General</span></div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:14px;">
        <div>
          <div style="font-size:12px;color:var(--text-muted);margin-bottom:6px;">Server name</div>
          <input class="inp" value="LLM Relay" />
        </div>
        <div>
          <div style="font-size:12px;color:var(--text-muted);margin-bottom:6px;">Admin email</div>
          <input class="inp" value="admin@llmrelay.local" />
        </div>
        <div>
          <div style="font-size:12px;color:var(--text-muted);margin-bottom:6px;">Default cost policy</div>
          <select class="inp"><option>free-first</option><option>local-first</option><option>cost-aware</option></select>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Observability</span></div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:12px;font-size:13px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div><div style="color:var(--text-primary);font-weight:600;">Langfuse tracing</div><div style="color:var(--text-muted);font-size:11px;">Emit traces from chat + agent runs</div></div>
          <div style="width:40px;height:22px;border-radius:11px;background:var(--accent);position:relative;cursor:pointer;"><div style="position:absolute;right:3px;top:3px;width:16px;height:16px;border-radius:50%;background:#fff;"></div></div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div><div style="color:var(--text-primary);font-weight:600;">Token count logging</div><div style="color:var(--text-muted);font-size:11px;">Include in/out tokens in activity feed</div></div>
          <div style="width:40px;height:22px;border-radius:11px;background:var(--accent);position:relative;cursor:pointer;"><div style="position:absolute;right:3px;top:3px;width:16px;height:16px;border-radius:50%;background:#fff;"></div></div>
        </div>
        <div>
          <div style="font-size:12px;color:var(--text-muted);margin-bottom:6px;">Langfuse URL</div>
          <input class="inp" value="https://cloud.langfuse.com" />
        </div>
      </div>
    </div>
  </div>
  <div class="col-half">
    <div class="card">
      <div class="card-header"><span class="card-title">Agent Defaults</span></div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:12px;">
        <div>
          <div style="font-size:12px;color:var(--text-muted);margin-bottom:6px;">Max steps</div>
          <input class="inp" value="20" />
        </div>
        <div>
          <div style="font-size:12px;color:var(--text-muted);margin-bottom:6px;">Agent timeout (seconds)</div>
          <input class="inp" value="120" />
        </div>
        <div>
          <div style="font-size:12px;color:var(--text-muted);margin-bottom:6px;">Default planner model</div>
          <input class="inp" value="nvidia/nemotron-super-120b-a12b" style="font-family:'IBM Plex Mono',monospace;font-size:11px;" />
        </div>
        <div>
          <div style="font-size:12px;color:var(--text-muted);margin-bottom:6px;">Default coder model</div>
          <input class="inp" value="qwen/qwen2.5-coder-32b-instruct" style="font-family:'IBM Plex Mono',monospace;font-size:11px;" />
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Integrations</span></div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:10px;font-size:13px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div><div style="color:var(--text-primary);font-weight:600;">Telegram bot</div><div style="color:var(--text-muted);font-size:11px;">Remote control via Telegram</div></div>
          <span class="chip" style="font-size:9px;padding:2px 7px;">Configure</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div><div style="color:var(--text-primary);font-weight:600;">GitHub integration</div><div style="color:var(--text-muted);font-size:11px;">PR review + issue automation</div></div>
          <span class="chip success" style="font-size:9px;padding:2px 7px;">Connected</span>
        </div>
      </div>
    </div>
  </div>
</div>
<button class="btn-primary" style="margin-top:4px;">Save settings</button>"""

# ── 13. ADMIN ─────────────────────────────────────────────────────────────────

ADMIN_BODY = """
<div class="row">
  <div style="flex:1.3;">
    <div class="card">
      <div class="card-header">
        <span class="card-title">API Keys</span>
        <button class="btn-primary" style="font-size:11px;padding:7px 14px;">+ Generate key</button>
      </div>
      <div class="card-body" style="padding:0;">
        <table class="tbl">
          <thead><tr><th>Key</th><th>Label</th><th>Created</th><th>Last used</th><th>Requests</th><th></th></tr></thead>
          <tbody>
            <tr>
              <td><span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--accent);">sk-relay-dev••••••••</span></td>
              <td style="color:var(--text-secondary);font-size:12px;">Development</td>
              <td style="color:var(--text-muted);font-size:11px;">2026-04-01</td>
              <td style="color:var(--text-muted);font-size:11px;">2 min ago</td>
              <td style="color:var(--text-primary);font-size:12px;">1,284</td>
              <td><button class="btn-ghost" style="font-size:11px;color:var(--danger);">Revoke</button></td>
            </tr>
            <tr>
              <td><span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--accent);">sk-relay-ci••••••••</span></td>
              <td style="color:var(--text-secondary);font-size:12px;">CI / GitHub Actions</td>
              <td style="color:var(--text-muted);font-size:11px;">2026-04-15</td>
              <td style="color:var(--text-muted);font-size:11px;">1 hour ago</td>
              <td style="color:var(--text-primary);font-size:12px;">342</td>
              <td><button class="btn-ghost" style="font-size:11px;color:var(--danger);">Revoke</button></td>
            </tr>
            <tr>
              <td><span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--accent);">sk-relay-team•••••••</span></td>
              <td style="color:var(--text-secondary);font-size:12px;">Team shared</td>
              <td style="color:var(--text-muted);font-size:11px;">2026-05-01</td>
              <td style="color:var(--text-muted);font-size:11px;">14 min ago</td>
              <td style="color:var(--text-primary);font-size:12px;">89</td>
              <td><button class="btn-ghost" style="font-size:11px;color:var(--danger);">Revoke</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
  <div style="flex:0.7;">
    <div class="card">
      <div class="card-header"><span class="card-title">System Health</span></div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:10px;font-size:13px;">
        <div style="display:flex;align-items:center;justify-content:space-between;"><span style="color:var(--text-muted);">Proxy</span><span class="chip success" style="font-size:9px;padding:2px 7px;"><span class="dot green"></span>running</span></div>
        <div style="display:flex;align-items:center;justify-content:space-between;"><span style="color:var(--text-muted);">Backend API</span><span class="chip success" style="font-size:9px;padding:2px 7px;"><span class="dot green"></span>running</span></div>
        <div style="display:flex;align-items:center;justify-content:space-between;"><span style="color:var(--text-muted);">Ollama</span><span class="chip success" style="font-size:9px;padding:2px 7px;"><span class="dot green"></span>running</span></div>
        <div style="display:flex;align-items:center;justify-content:space-between;"><span style="color:var(--text-muted);">MongoDB</span><span class="chip success" style="font-size:9px;padding:2px 7px;"><span class="dot green"></span>connected</span></div>
        <div style="display:flex;align-items:center;justify-content:space-between;"><span style="color:var(--text-muted);">NVIDIA NIM</span><span class="chip success" style="font-size:9px;padding:2px 7px;"><span class="dot green"></span>healthy</span></div>
        <div style="display:flex;align-items:center;justify-content:space-between;"><span style="color:var(--text-muted);">Docker</span><span class="chip warning" style="font-size:9px;padding:2px 7px;"><span class="dot yellow"></span>unavailable</span></div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Server Info</span></div>
      <div class="card-body" style="font-size:12px;display:flex;flex-direction:column;gap:7px;font-family:'IBM Plex Mono',monospace;">
        <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Version</span><span style="color:var(--text-primary);">v4.0.0</span></div>
        <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Python</span><span style="color:var(--text-primary);">3.13</span></div>
        <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Uptime</span><span style="color:var(--success);">14d 6h</span></div>
        <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-muted);">Port</span><span style="color:var(--text-primary);">8000</span></div>
      </div>
    </div>
  </div>
</div>"""

# ── 14. LOGIN (desktop) ───────────────────────────────────────────────────────

LOGIN_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
{BASE_CSS}
body{{min-height:100vh;display:flex;align-items:stretch;}}
.login-left{{width:420px;flex-shrink:0;background:var(--bg-sidebar);border-right:1px solid var(--border);
  display:flex;flex-direction:column;justify-content:center;padding:48px 40px;}}
.login-right{{flex:1;display:flex;align-items:center;justify-content:center;background:var(--bg-base);padding:40px;}}
.login-card{{width:100%;max-width:420px;background:linear-gradient(180deg,rgba(27,32,41,0.96),rgba(13,16,21,0.96));
  border:1px solid rgba(255,255,255,0.1);border-radius:28px;padding:36px;
  box-shadow:0 22px 70px rgba(0,0,0,0.32);}}
.field{{margin-bottom:16px;}}
.field label{{display:block;font-size:11px;font-weight:700;color:var(--text-muted);
  letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;font-family:'IBM Plex Mono',monospace;}}
.divider{{display:flex;align-items:center;gap:12px;margin:18px 0;}}
.divider-line{{flex:1;height:1px;background:var(--border);}}
.divider-text{{font-size:11px;color:var(--text-muted);}}
.social-btn{{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;padding:11px;
  border-radius:14px;background:rgba(255,255,255,0.04);border:1px solid var(--border);
  color:var(--text-secondary);font-size:13px;font-weight:600;margin-bottom:8px;cursor:pointer;}}
.feature-item{{display:flex;align-items:flex-start;gap:12px;margin-bottom:20px;}}
.feature-icon{{width:36px;height:36px;border-radius:10px;background:rgba(93,162,255,0.1);
  border:1px solid rgba(93,162,255,0.2);display:flex;align-items:center;justify-content:center;flex-shrink:0;}}
.feature-icon svg{{width:16px;height:16px;stroke:var(--accent);fill:none;stroke-width:2;}}
</style>
</head><body>
<div class="login-left">
  <div style="margin-bottom:40px;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
      <div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#1a3a6b,#0d2048);
        border:1px solid rgba(93,162,255,0.25);display:flex;align-items:center;justify-content:center;">
        <svg viewBox="0 0 24 24" width="18" height="18" stroke="#5da2ff" fill="none" stroke-width="2">
          <rect x="4" y="4" width="6" height="6"/><rect x="14" y="4" width="6" height="6"/>
          <rect x="14" y="14" width="6" height="6"/><rect x="4" y="14" width="6" height="6"/>
        </svg>
      </div>
      <div>
        <div style="font-size:18px;font-weight:800;color:var(--text-primary);">LLM Relay</div>
        <div style="font-size:10px;color:var(--text-muted);font-family:'IBM Plex Mono',monospace;letter-spacing:0.12em;">v4.0 · native black</div>
      </div>
    </div>
    <div style="font-size:14px;color:var(--text-muted);margin-top:16px;line-height:1.6;">
      Your AI control room. One place to run local AI, connect your tools, and keep your data close.
    </div>
  </div>
  <div class="feature-item">
    <div class="feature-icon"><svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg></div>
    <div><div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:2px;">NVIDIA NIM free tier</div><div style="font-size:12px;color:var(--text-muted);">World-class models at zero cost</div></div>
  </div>
  <div class="feature-item">
    <div class="feature-icon"><svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M6 20v-2a6 6 0 0 1 12 0v2"/></svg></div>
    <div><div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:2px;">Async agent jobs</div><div style="font-size:12px;color:var(--text-muted);">Non-blocking tasks with live progress</div></div>
  </div>
  <div class="feature-item">
    <div class="feature-icon"><svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16"/></svg></div>
    <div><div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:2px;">Smart routing</div><div style="font-size:12px;color:var(--text-muted);">free-first → local → cloud fallback</div></div>
  </div>
  <div class="feature-item" style="margin-bottom:0;">
    <div class="feature-icon"><svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>
    <div><div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:2px;">Full observability</div><div style="font-size:12px;color:var(--text-muted);">Langfuse traces from every message</div></div>
  </div>
</div>
<div class="login-right">
  <div class="login-card">
    <div style="font-size:20px;font-weight:800;color:var(--text-primary);margin-bottom:4px;">Welcome back</div>
    <div style="font-size:13px;color:var(--text-muted);margin-bottom:24px;">Sign in to your control room</div>
    <div class="field">
      <label>Email</label>
      <input class="inp" value="admin@llmrelay.local" />
    </div>
    <div class="field">
      <label>Password</label>
      <input class="inp" type="password" value="••••••••••••" />
    </div>
    <button class="btn-primary" style="width:100%;justify-content:center;margin-top:8px;">Sign in</button>
    <div class="divider"><div class="divider-line"></div><span class="divider-text">or continue with</span><div class="divider-line"></div></div>
    <div class="social-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/></svg>
      Continue with GitHub
    </div>
    <div class="social-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
      Continue with Google
    </div>
  </div>
</div>
</body></html>"""

# ── 15. SETUP WIZARD ──────────────────────────────────────────────────────────

SETUP_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
{BASE_CSS}
body{{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;
  padding:40px 24px;background:var(--bg-base);}}
.wizard-wrap{{width:100%;max-width:760px;}}
.steps{{display:flex;align-items:center;gap:0;margin-bottom:32px;}}
.step{{display:flex;flex-direction:column;align-items:center;flex:1;}}
.step-circle{{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:12px;font-weight:700;border:2px solid;}}
.step-circle.done{{background:var(--accent);border-color:var(--accent);color:#06111f;}}
.step-circle.active{{background:rgba(93,162,255,0.12);border-color:var(--accent);color:var(--accent);}}
.step-circle.future{{background:transparent;border-color:rgba(255,255,255,0.15);color:var(--text-muted);}}
.step-label{{font-size:10px;color:var(--text-muted);margin-top:6px;font-family:'IBM Plex Mono',monospace;letter-spacing:0.08em;}}
.step-label.active{{color:var(--accent);}}
.step-line{{flex:1;height:1px;background:rgba(255,255,255,0.1);margin:0 -1px;margin-bottom:20px;}}
.step-line.done{{background:var(--accent);}}
.wizard-card{{background:linear-gradient(180deg,rgba(21,25,34,0.94),rgba(10,12,15,0.94));
  border:1px solid var(--border);border-radius:var(--radius-lg);padding:32px;}}
.provider-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;}}
.provider-card{{padding:18px;border-radius:18px;border:2px solid;cursor:pointer;}}
.provider-card.selected{{border-color:var(--accent);background:rgba(93,162,255,0.07);}}
.provider-card.unselected{{border-color:var(--border);background:rgba(255,255,255,0.02);}}
.provider-badges{{display:flex;gap:5px;margin-bottom:10px;}}
.badge-green{{padding:2px 8px;border-radius:999px;background:rgba(70,217,164,0.12);
  border:1px solid rgba(70,217,164,0.25);color:var(--success);font-size:9px;font-weight:700;
  letter-spacing:0.1em;text-transform:uppercase;font-family:'IBM Plex Mono',monospace;}}
.badge-blue{{padding:2px 8px;border-radius:999px;background:rgba(93,162,255,0.12);
  border:1px solid rgba(93,162,255,0.25);color:var(--accent);font-size:9px;font-weight:700;
  letter-spacing:0.1em;text-transform:uppercase;font-family:'IBM Plex Mono',monospace;}}
</style>
</head><body>
<div class="wizard-wrap">
  <div style="text-align:center;margin-bottom:28px;">
    <div style="font-size:22px;font-weight:800;color:var(--text-primary);margin-bottom:4px;">Set up LLM Relay</div>
    <div style="font-size:13px;color:var(--text-muted);">Step 1 of 5 · Choose your AI providers</div>
  </div>
  <!-- Steps -->
  <div class="steps">
    <div class="step">
      <div class="step-circle active">1</div>
      <div class="step-label active">Providers</div>
    </div>
    <div class="step-line"></div>
    <div class="step">
      <div class="step-circle future">2</div>
      <div class="step-label">Models</div>
    </div>
    <div class="step-line"></div>
    <div class="step">
      <div class="step-circle future">3</div>
      <div class="step-label">Runtime</div>
    </div>
    <div class="step-line"></div>
    <div class="step">
      <div class="step-circle future">4</div>
      <div class="step-label">Agent</div>
    </div>
    <div class="step-line"></div>
    <div class="step">
      <div class="step-circle future">5</div>
      <div class="step-label">Policy</div>
    </div>
  </div>
  <div class="wizard-card">
    <div style="font-size:15px;font-weight:700;color:var(--text-primary);margin-bottom:6px;">Which AI providers do you want to use?</div>
    <div style="font-size:13px;color:var(--text-muted);margin-bottom:20px;">You can add more later. NVIDIA NIM requires a free API key — no GPU needed.</div>
    <div class="provider-grid">
      <!-- NIM (selected + auto-detected) -->
      <div class="provider-card selected" style="grid-column:1/-1;">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;">
          <div>
            <div class="provider-badges">
              <span class="badge-blue">★ Recommended</span>
              <span class="badge-green">Free</span>
              <span class="badge-green">✓ Auto-detected</span>
            </div>
            <div style="font-size:15px;font-weight:700;color:var(--text-primary);margin-bottom:4px;">NVIDIA NIM</div>
            <div style="font-size:12px;color:var(--text-muted);line-height:1.6;">
              World-class models (Qwen2.5-Coder 32B, Nemotron 120B, DeepSeek-R1) at zero cost.
              No GPU required. NVIDIA_API_KEY detected on this server.
            </div>
          </div>
          <div style="width:22px;height:22px;border-radius:50%;background:var(--accent);
            display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-left:16px;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#06111f" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          </div>
        </div>
      </div>
      <!-- Ollama -->
      <div class="provider-card selected">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;">
          <div>
            <div class="provider-badges"><span class="badge-green">Local / private</span></div>
            <div style="font-size:14px;font-weight:700;color:var(--text-primary);margin-bottom:4px;">Ollama</div>
            <div style="font-size:12px;color:var(--text-muted);">Run models on your own hardware. Full data privacy.</div>
          </div>
          <div style="width:22px;height:22px;border-radius:50%;background:var(--accent);
            display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-left:12px;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#06111f" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          </div>
        </div>
      </div>
      <!-- Anthropic -->
      <div class="provider-card unselected">
        <div>
          <div class="provider-badges"><span style="padding:2px 8px;border-radius:999px;background:rgba(255,255,255,0.05);border:1px solid var(--border);color:var(--text-muted);font-size:9px;text-transform:uppercase;font-family:'IBM Plex Mono',monospace;letter-spacing:0.1em;">Cloud · paid</span></div>
          <div style="font-size:14px;font-weight:700;color:var(--text-primary);margin-bottom:4px;">Anthropic</div>
          <div style="font-size:12px;color:var(--text-muted);">Claude Opus, Sonnet, Haiku via API key.</div>
        </div>
      </div>
    </div>
    <div style="display:flex;justify-content:flex-end;margin-top:24px;">
      <button class="btn-primary">Next: Model Selection →</button>
    </div>
  </div>
</div>
</body></html>"""


def build_screens() -> None:
    # 1. Dashboard
    shot("v4-control-plane.png", page("home", "Dashboard", "LLM Relay v4.0", DASHBOARD_BODY,
         '<button class="btn-secondary" style="font-size:12px;">Refresh</button>'))

    # 2. Chat (full-viewport layout)
    chat_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>{BASE_CSS}</style></head><body>
<div class="layout">
  {sidebar("chat")}
  <div class="main" style="overflow:hidden;">
    {CHAT_BODY}
  </div>
</div></body></html>"""
    shot("v4-chat.png", chat_html)

    # 3. Tasks
    shot("v4-tasks-kanban.png", page("tasks", "Task Board", "Multica workflow", TASKS_BODY,
         '<button class="btn-primary" style="font-size:12px;">+ New task</button>'))

    # 4. Agents
    shot("v4-agents.png", page("agents", "Agents", "3 configured", AGENTS_BODY,
         '<button class="btn-primary" style="font-size:12px;">+ New agent</button>'))

    # 5. Runtimes
    shot("v4-runtimes.png", page("runtimes", "Runtimes", "Execution environments", RUNTIMES_BODY))

    # 6. Routing
    shot("v4-routing.png", page("routing", "Routing Policy", "Provider selection rules", ROUTING_BODY,
         '<button class="btn-secondary" style="font-size:12px;">Save policy</button>'))

    # 7. Providers
    shot("v4-providers.png", page("providers", "Providers", "Connected AI sources", PROVIDERS_BODY))

    # 8. Models
    shot("v4-models.png", page("providers", "Models", "Available models across providers", MODELS_BODY,
         '<button class="btn-primary" style="font-size:12px;">Sync models</button>'))

    # 9. Knowledge
    shot("v4-knowledge.png", page("knowledge", "Knowledge", "Wiki &amp; source library", KNOWLEDGE_BODY,
         '<button class="btn-primary" style="font-size:12px;">+ Import source</button>'))

    # 10. Logs
    shot("v4-logs.png", page("logs", "Logs &amp; Activity", "Real-time event feed + Langfuse traces", LOGS_BODY))

    # 11. Schedules
    shot("v4-schedules.png", page("schedules", "Schedules", "Automated agent jobs", SCHEDULES_BODY))

    # 12. Settings
    shot("v4-settings.png", page("settings", "Settings", "Server configuration", SETTINGS_BODY))

    # 13. Admin
    shot("v4-admin.png", page("settings", "Admin", "Keys &amp; system management", ADMIN_BODY,
         '<button class="btn-secondary" style="font-size:12px;">+ Generate key</button>'))

    # 14. Login
    shot("v4-login.png", LOGIN_HTML)

    # 15. Setup Wizard
    shot("v4-setup-wizard.png", SETUP_HTML)


if __name__ == "__main__":
    build_screens()
    print(f"\n✓ All 15 screenshots saved to {OUT}/")

